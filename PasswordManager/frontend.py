import os
import json
import base64
import requests
import typer
import hashlib
import pyperclip
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SERVER_URL = "http://192.168.100.96:3333" 
USB_KEY_PATH = "/Volumes/ECHO1/pass.key"
USERNAME = "phoenix"

app = typer.Typer()

# --- Cryptography Engine ---
class CryptoEngine:
    def __init__(self, key_file_path):
        if not os.path.exists(key_file_path):
            typer.secho(f"FATAL: Security key not found!", fg=typer.colors.RED, bold=True)
            typer.secho("Please insert ECHO1 and try again.", fg=typer.colors.RED, bold=True)
            raise typer.Exit(code=1)
            
        with open(key_file_path, "rb") as f:
            master_secret = f.read()
            
        self.k_enc = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"JASON_VAULT_ENCRYPTION_KEY",
        ).derive(master_secret)
        
        self.k_auth = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"JASON_SERVER_AUTH_KEY",
        ).derive(master_secret)
        
        self.auth_hash = hashlib.sha256(self.k_auth).hexdigest()

    def encrypt(self, data_dict: dict) -> str:
        json_bytes = json.dumps(data_dict).encode('utf-8')
        aesgcm = AESGCM(self.k_enc)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, json_bytes, associated_data=None)
        return base64.b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt(self, blob_b64: str) -> dict:
        if not blob_b64:
            return {} # Empty vault
            
        raw_data = base64.b64decode(blob_b64)
        nonce = raw_data[:12]
        ciphertext = raw_data[12:]
        
        aesgcm = AESGCM(self.k_enc)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
            return json.loads(plaintext.decode('utf-8'))
        except Exception:
            typer.secho("Decryption Failed! Integrity check failed.", fg=typer.colors.RED)
            raise typer.Exit(code=1)

class VaultSync:
    def __init__(self, crypto: CryptoEngine):
        self.crypto = crypto
        self.session = requests.Session()

    def pull(self) -> dict:
        payload = {
            "username": USERNAME,
            "client_auth_hash": self.crypto.auth_hash
        }
        try:
            resp = self.session.post(f"{SERVER_URL}/vault/download", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return self.crypto.decrypt(data.get("vault_blob", ""))
        except requests.exceptions.ConnectionError:
            typer.secho("Server Offline. Cannot Sync.", fg=typer.colors.YELLOW)
            return {}

    def push(self, data: dict):
        encrypted_blob = self.crypto.encrypt(data)
        payload = {
            "username": USERNAME,
            "client_auth_hash": self.crypto.auth_hash,
            "vault_blob": encrypted_blob
        }
        resp = self.session.post(f"{SERVER_URL}/vault/upload", json=payload)
        resp.raise_for_status()
        typer.secho("Synced with Server", fg=typer.colors.GREEN)


@app.command()
def init():
    crypto = CryptoEngine(USB_KEY_PATH)
    payload = {"username": USERNAME, "client_auth_hash": crypto.auth_hash}
    resp = requests.post(f"{SERVER_URL}/register", json=payload)
    typer.echo(resp.json())

@app.command()
def add(
    site: str = typer.Option(..., prompt="What is the site/service name?"),
    password: str = typer.Option(..., prompt="Enter the password", hide_input=True, confirmation_prompt=True)
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    
    vault = sync.pull()
    
    vault[site] = password
    typer.secho(f"Added password for {site}", fg=typer.colors.GREEN)
    
    sync.push(vault)

@app.command()
def get(
    site: str = typer.Option(..., prompt="Which site do you need?")
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    
    vault = sync.pull()
    if site in vault:
        pwd = vault[site]
        # print(f"Password: {pwd}")  <-- Optional: Comment this out if you only want it on clipboard
        try:
            pyperclip.copy(pwd)
            typer.secho(f"✨ Password for '{site}' copied to clipboard!", fg=typer.colors.GREEN, bold=True)
        except pyperclip.PyperclipException:
            typer.secho("Could not copy to clipboard. Here it is:", fg=typer.colors.YELLOW)
            typer.secho(pwd, fg=typer.colors.WHITE, bg=typer.colors.BLACK)
    else:
        typer.secho(f"Site '{site}' not found in vault.", fg=typer.colors.RED)

@app.command()
def delete(
    site: str = typer.Option(..., prompt="🗑️ Which site do you want to delete?")
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    
    # 1. Get current vault
    vault = sync.pull()
    
    # 2. Check if exists
    if site not in vault:
        typer.secho(f"Site '{site}' not found in vault.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # 3. Confirm deletion
    delete_confirm = typer.confirm(f"Are you sure you want to PERMANENTLY delete the password for '{site}'?", default=False)
    
    if not delete_confirm:
        typer.echo("Operation cancelled.")
        raise typer.Exit()

    # 4. Delete and Sync
    del vault[site]
    sync.push(vault)
    typer.secho(f"Password for '{site}' deleted.", fg=typer.colors.GREEN)

@app.command()
def ls():
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    vault = sync.pull()
    
    typer.echo("Your Vault:")
    for site in vault.keys():
        typer.echo(f" - {site}")

if __name__ == "__main__":
    if not os.path.exists(USB_KEY_PATH):
        typer.secho(f"FATAL: Security key not found!", fg=typer.colors.RED, bold=True)
        typer.secho("Please insert ECHO1 and try again.", fg=typer.colors.RED, bold=True)
        exit()

    app()
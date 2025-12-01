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
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = "http://192.168.100.96:3333" 
USB_KEY_PATH = os.getenv("USB_KEY_PATH", "")
USERNAME = os.getenv("USERNAME", "")

app = typer.Typer()

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

# API Key Sub-Command Group 
api_app = typer.Typer()
app.add_typer(api_app, name="api", help="Manage API Keys and Secrets")

@api_app.command("add")
def add_api(
    name: str = typer.Option(..., prompt="Service Name"),
    key: str = typer.Option(..., prompt="API Key / Public Key", hide_input=True),
    secret: str = typer.Option("", prompt="Secret Key (Optional, press Enter to skip)", hide_input=True)
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    
    vault = sync.pull()
    
    vault[name] = {
        "type": "apikey",
        "key": key,
        "secret": secret
    }
    
    sync.push(vault)
    typer.secho(f"Success: API credentials for '{name}' saved.", fg=typer.colors.GREEN)

@api_app.command("get")
def get_api(
    name: str = typer.Option(..., prompt="Which API key do you need?")
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    vault = sync.pull()
    
    if name not in vault:
        typer.secho(f"Error: '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    data = vault[name]
    
    if data.get("type") != "apikey":
        typer.secho(f"Warning: '{name}' is not an API key entry.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    typer.secho(f"API: {name}", fg=typer.colors.BLUE, bold=True)

    # Copy Key Logic
    try:
        pyperclip.copy(data['key'])
        typer.secho("Public Key copied to clipboard!", fg=typer.colors.GREEN)
    except pyperclip.PyperclipException:
        typer.echo(f"Key: {data['key']}")

    # Handle Secret
    if data['secret']:
        if typer.confirm("Show Secret Key?"):
            typer.secho(f"Secret: {data['secret']}", fg=typer.colors.MAGENTA)
    else:
        typer.echo("No secret key stored.")

@api_app.command("ls")
def list_apis():
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    vault = sync.pull()
    
    apis = []
    for name, data in vault.items():
        if isinstance(data, dict) and data.get("type") == "apikey":
            apis.append(name)
            
    if not apis:
        typer.secho("No API keys found.", fg=typer.colors.YELLOW)
        raise typer.Exit()
        
    typer.secho("Your API Keys:", fg=typer.colors.BLUE, bold=True)
    for api in apis:
        typer.echo(f" - {api}")

@api_app.command("edit")
def edit_api(
    name: str = typer.Option(..., prompt="Which API entry to edit?")
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    vault = sync.pull()

    if name not in vault:
        typer.secho(f"Error: '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    entry = vault[name]
    if entry.get("type") != "apikey":
        typer.secho(f"Error: '{name}' is not an API key.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Rename
    new_name = typer.prompt(f"New Name (Press Enter to keep '{name}')", default=name, show_default=False)
    if new_name != name and new_name in vault:
        typer.secho(f"Error: '{new_name}' already exists.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Update Fields
    new_key = typer.prompt("API Key", default=entry.get("key", ""), hide_input=True, show_default=False)
    new_secret = typer.prompt("Secret Key", default=entry.get("secret", ""), hide_input=True, show_default=False)

    # Save
    if new_name != name:
        del vault[name]

    vault[new_name] = {
        "type": "apikey",
        "key": new_key,
        "secret": new_secret
    }
    
    sync.push(vault)
    typer.secho("Success: API details updated.", fg=typer.colors.GREEN)

# Card Sub-Command Group
card_app = typer.Typer()
app.add_typer(card_app, name="card", help="Manage credit and debit cards")

@card_app.command("add")
def add_card(
    name: str = typer.Option(..., prompt="Card Name"),
    holder: str = typer.Option(..., prompt="Cardholder Name"),
    number: str = typer.Option(..., prompt="Card Number", hide_input=True),
    expiry: str = typer.Option(..., prompt="Expiry Date (MM/YY)"),
    cvv: str = typer.Option(..., prompt="CVV/CVC", hide_input=True),
    pin: str = typer.Option("", prompt="PIN (Optional, press Enter to skip)", hide_input=True)
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    
    vault = sync.pull()
    
    vault[name] = {
        "type": "card",
        "holder": holder,
        "number": number,
        "expiry": expiry,
        "cvv": cvv,
        "pin": pin
    }
    
    sync.push(vault)
    typer.secho(f"Card '{name}' saved securely.", fg=typer.colors.GREEN)

@card_app.command("get")
def get_card(
    name: str = typer.Option(..., prompt="Which card do you need?")
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    vault = sync.pull()
    
    if name not in vault:
        typer.secho(f"'{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    data = vault[name]
    
    if data.get("type") != "card":
        typer.secho(f"'{name}' is a password entry, not a card. Use 'pass get' instead.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    typer.secho(f"{name}", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"Holder: {data['holder']}")
    typer.echo(f"Expiry: {data['expiry']}")

    try:
        pyperclip.copy(data['number'])
        typer.secho("Card number copied to clipboard!", fg=typer.colors.GREEN)
    except pyperclip.PyperclipException:
        typer.echo(f"Number: {data['number']}")

    if typer.confirm("Show CVV and PIN?"):
        typer.secho(f"CVV: {data['cvv']}", fg=typer.colors.MAGENTA)
        if data['pin']:
            typer.secho(f"PIN: {data['pin']}", fg=typer.colors.MAGENTA)
        else:
            typer.secho("PIN: Not Set", fg=typer.colors.MAGENTA)

@card_app.command("edit")
def edit_card(
    name: str = typer.Option(..., prompt="Which card do you want to edit?")
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    vault = sync.pull()

    if name not in vault:
        typer.secho(f"Error: Card '{name}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    entry = vault[name]
    if entry.get("type") != "card":
        typer.secho(f"Error: '{name}' is not a card.", fg=typer.colors.RED)
        raise typer.Exit(1)

    new_name = typer.prompt(f"New Name (Press Enter to keep '{name}')", default=name, show_default=False)
    if new_name != name and new_name in vault:
        typer.secho(f"Error: '{new_name}' already exists.", fg=typer.colors.RED)
        raise typer.Exit(1)

    holder = typer.prompt("Holder Name", default=entry.get("holder", ""))
    number = typer.prompt("Card Number", default=entry.get("number", ""))
    expiry = typer.prompt("Expiry (MM/YY)", default=entry.get("expiry", ""))
    
    new_cvv = typer.prompt("CVV (Leave blank to keep current)", default="", hide_input=True, show_default=False)
    cvv = new_cvv if new_cvv else entry.get("cvv", "")

    new_pin = typer.prompt("PIN (Leave blank to keep current)", default="", hide_input=True, show_default=False)
    pin = new_pin if new_pin else entry.get("pin", "")

    if new_name != name:
        del vault[name]

    vault[new_name] = {
        "type": "card",
        "holder": holder,
        "number": number,
        "expiry": expiry,
        "cvv": cvv,
        "pin": pin
    }
    
    sync.push(vault)
    typer.secho("Success: Card details updated.", fg=typer.colors.GREEN)

@card_app.command("ls")
def list_cards():
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    vault = sync.pull()
    
    cards = []
    for name, data in vault.items():
        if isinstance(data, dict) and data.get("type") == "card":
            cards.append(name)
            
    if not cards:
        typer.secho("No cards found.", fg=typer.colors.YELLOW)
        raise typer.Exit()
        
    typer.secho("Your Cards:", fg=typer.colors.BLUE, bold=True)
    for card in cards:
        typer.echo(f" - {card}")

# Main Password Manager Commands
@app.command()
def init(
    username: str = typer.Option(..., prompt="Enter your username:"),
):
    crypto = CryptoEngine(USB_KEY_PATH)
    payload = {"username": username, "client_auth_hash": crypto.auth_hash}
    resp = requests.post(f"{SERVER_URL}/register", json=payload)
    typer.echo(resp.json())
    with open(".env", "w") as f:
        f.write("USERNAME=" + username + "\n")

@app.command()
def add(
    site: str = typer.Option(..., prompt="What is the site/service name?"),
    username: str = typer.Option(..., prompt="Enter the username/email"),
    password: str = typer.Option(..., prompt="Enter the password", hide_input=True, confirmation_prompt=True)
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    
    vault = sync.pull()
    
    vault[site] = {
        "username": username,
        "password": password
    }
    
    typer.secho(f"Saved credentials for {site}", fg=typer.colors.GREEN)
    sync.push(vault)

@app.command()
def get(
    site: str = typer.Option(..., prompt="Which site do you need?")
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    
    vault = sync.pull()
    if site in vault:
        entry = vault[site]
        
        if isinstance(entry, dict):
            user = entry.get("username", "Unknown")
            pwd = entry.get("password", "")
        else:
            user = "N/A (Old Data Format)"
            pwd = entry
            
        typer.secho(f"Username: {user}", fg=typer.colors.CYAN)
        
        try:
            pyperclip.copy(pwd)
            typer.secho(f"Password for '{site}' copied to clipboard!", fg=typer.colors.GREEN, bold=True)
        except pyperclip.PyperclipException:
            typer.secho("Could not copy to clipboard. Here it is:", fg=typer.colors.YELLOW)
            typer.secho(pwd, fg=typer.colors.WHITE, bg=typer.colors.BLACK)
    else:
        typer.secho(f"Site '{site}' not found in vault.", fg=typer.colors.RED)

@app.command()
def delete(
    site: str = typer.Option(..., prompt="Which site do you want to delete?")
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    
    vault = sync.pull()
    
    if site not in vault:
        typer.secho(f"Site '{site}' not found in vault.", fg=typer.colors.RED)
        raise typer.Exit(1)

    delete_confirm = typer.confirm(f"Are you sure you want to PERMANENTLY delete the password for '{site}'?", default=False)
    
    if not delete_confirm:
        typer.echo("Operation cancelled.")
        raise typer.Exit()

    del vault[site]
    sync.push(vault)
    typer.secho(f"Password for '{site}' deleted.", fg=typer.colors.GREEN)

@app.command()
def edit(
    site: str = typer.Option(..., prompt="Which site do you want to edit?")
):
    crypto = CryptoEngine(USB_KEY_PATH)
    sync = VaultSync(crypto)
    vault = sync.pull()

    if site not in vault:
        typer.secho(f"Error: Site '{site}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Detect if this is actually a card
    if isinstance(vault[site], dict) and vault[site].get("type") == "card":
        typer.secho(f"This is a card. Please use: pass card edit", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    new_name = typer.prompt(f"New Name (Press Enter to keep '{site}')", default=site, show_default=False)
    
    if new_name != site and new_name in vault:
        typer.secho(f"Error: An entry named '{new_name}' already exists.", fg=typer.colors.RED)
        raise typer.Exit(1)

    entry = vault[site]
    
    if isinstance(entry, dict):
        current_user = entry.get("username", "")
        current_pass = entry.get("password", "")
    else:
        current_user = ""
        current_pass = entry

    new_user = typer.prompt(f"Username", default=current_user)
    new_pass = typer.prompt(f"Password", default=current_pass, hide_input=True, show_default=False)

    if new_name != site:
        del vault[site]
        typer.echo(f"Renaming entry to '{new_name}'...")

    vault[new_name] = {
        "username": new_user,
        "password": new_pass
    }
    
    sync.push(vault)
    typer.secho("Success: Entry updated.", fg=typer.colors.GREEN)

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
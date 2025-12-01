import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from contextlib import asynccontextmanager

# DB_PATH = '/mnt/nas/data.db'  
DB_PATH = 'jason_vault.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                auth_hash TEXT NOT NULL,
                vault_blob TEXT
            )
        ''')
        conn.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan, title="PasswordManager")

class RegisterRequest(BaseModel):
    username: str
    client_auth_hash: str

class VaultSyncRequest(BaseModel):
    username: str
    client_auth_hash: str
    vault_blob: Optional[str] = None

def verify_user(cursor, username: str, provided_hash: str):
    cursor.execute("SELECT auth_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    
    if row['auth_hash'] != provided_hash:
        raise HTTPException(status_code=401, detail="Invalid Authentication")
    
    return True


@app.get("/")
def health_check():
    return {"status": "online", "system": "PasswordManager"}

@app.post("/register")
def register_user(req: RegisterRequest):
    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, auth_hash, vault_blob) VALUES (?, ?, ?)",
                (req.username, req.client_auth_hash, "")
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Username already exists")
            
    return {"message": f"User '{req.username}' registered successfully."}

@app.post("/vault/upload")
def upload_vault(req: VaultSyncRequest):
    if not req.vault_blob:
        raise HTTPException(status_code=400, detail="No vault blob provided")

    with get_db() as conn:
        cursor = conn.cursor()
        verify_user(cursor, req.username, req.client_auth_hash)
        
        cursor.execute(
            "UPDATE users SET vault_blob = ? WHERE username = ?",
            (req.vault_blob, req.username)
        )
        conn.commit()
        
    return {"status": "synced", "bytes_stored": len(req.vault_blob)}

@app.post("/vault/download")
def download_vault(req: VaultSyncRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        verify_user(cursor, req.username, req.client_auth_hash)
        
        cursor.execute("SELECT vault_blob FROM users WHERE username = ?", (req.username,))
        row = cursor.fetchone()
        
    blob = row['vault_blob'] if row and row['vault_blob'] else ""
    return {"vault_blob": blob}
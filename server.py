import base64
import logging
import hashlib
import sys
from typing import Optional
from fastapi import FastAPI, File, Request, UploadFile,HTTPException
from fastapi.params import Header
from fastapi.responses import FileResponse, JSONResponse,PlainTextResponse
import httpx
from pydantic import BaseModel
from dotenv import load_dotenv

import shutil
import os
import time
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad,pad
from base64 import b64decode, b64encode

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
load_dotenv()

app = FastAPI()
API_KEY = os.getenv("API_KEY") #when more cameras are added use the mac address of the camera and a lookup db
NOTIFICATION_TOKEN = os.getenv("NOTIFICATION_TOKEN") #token for the ntfy service
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL") #base url for the ntfy service
PROXY_TRIGGER = os.getenv("PROXY_TRIGGER") #the path used in the reverse proxy to trigger this service


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s %(name)s:- %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("fastapi_app.log")])

logger = logging.getLogger("fastapi_app")

class MessageSchema(BaseModel):
    message : str
    topic : str    
    fn: Optional[str] = None

@app.get("/list")
async def list_images(x_api_key:str = Header(...)):
    if (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")
    files = os.listdir(UPLOAD_DIR)
    return JSONResponse(content={"files": files}, status_code=200)

@app.get("/get-file/{filename}")
async def get_file(filename: str, request:Request, x_api_key:str = Header(...)):
    if (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")    
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path)

@app.get("/get-file-by-encrypted-name/{filename}")
async def get_file_by_encrypted_file_name(filename: str):  #decrypted filename, no api key needed as this is used in the notification service
    file_path = os.path.join(UPLOAD_DIR, decrypt_string(filename))    
    if not os.path.isfile(file_path):
        logger.info(f"File not found for decrypted filename: {filename}")
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path)

@app.post("/notification")
async def post_notification(request:Request, message:MessageSchema, x_api_key:str = Header(...)):        
    if (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")        
    url = NOTIFICATION_URL        
    attachment_url = f"{request.url.scheme}://{request.url.hostname}/{PROXY_TRIGGER}/get-file-by-encrypted-name/{message.fn}"
    logger.info(f"Attachment URL: {attachment_url}")
    async with httpx.AsyncClient() as client:
        if not message.fn:
            client.headers = {
                "Authorization": f"Bearer {NOTIFICATION_TOKEN}",
                "Tags": "loudspeaker"
            }
        else:
            client.headers = {
                "Authorization": f"Bearer {NOTIFICATION_TOKEN}",
                "Tags": "loudspeaker",                
                "Attachment" : attachment_url
                }        
        _ = await client.post(url+message.topic, data=message.message) #to the self-hosted ntfy server
    return  PlainTextResponse(status_code=200)  

@app.post("/upload")
async def upload_image(file:UploadFile = File(...), x_api_key:str = Header(...)):
    if (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")    
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG and PNG are allowed.")
    
    old_path = Path(file.filename)
    new_name = old_path.with_name(f"{time.time() * 1000}{old_path.suffix}")
    file_path = os.path.join(UPLOAD_DIR, new_name.name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)        
    es = encrypt_string(os.path.basename(new_name.name))
    logger.info(es)
    return PlainTextResponse(es,status_code=201) 

def decrypt_string(token: str) -> str:
    key_env = os.getenv("CRYPTO_KEY")
    if not key_env:
        raise ValueError("CRYPTO_KEY env var not set")

    key = key_env.encode("utf-8")
    if len(key) not in (16, 24, 32):
        key = hashlib.sha256(key).digest()

    # Restore padding and decode
    try:
        token_bytes = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    except Exception as e:
        raise ValueError("Invalid token format") from e
    if len(token_bytes) < 32:  # nonce (16) + tag (16) + min ciphertext (16)
        raise ValueError("Invalid token length")

    nonce = token_bytes[:16]   # GCM nonce is 16 bytes by default
    tag   = token_bytes[16:32] # 16-byte auth tag
    ct    = token_bytes[32:]
    try:        
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ct, tag)
    except ValueError as e:
        raise ValueError("Decryption failed or data is tampered") from e    
    return plaintext.decode("utf-8")

def encrypt_string(plain_text: str) -> str:
    key_env = os.getenv("CRYPTO_KEY")
    if not key_env:
        raise ValueError("CRYPTO_KEY env var not set")

    key = key_env.encode("utf-8")
    if len(key) not in (16, 24, 32):
        key = hashlib.sha256(key).digest()

    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(plain_text.encode("utf-8"))
    # Build token: nonce + tag + ciphertext
    token = cipher.nonce + tag + ciphertext
    return base64.urlsafe_b64encode(token).decode("utf-8").rstrip("=")
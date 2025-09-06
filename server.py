from fastapi import FastAPI, File, UploadFile,HTTPException
from fastapi.params import Header
from fastapi.responses import FileResponse, JSONResponse,PlainTextResponse
import httpx
from pydantic import BaseModel
from dotenv import load_dotenv

import shutil
import os
import time
from pathlib import Path


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
load_dotenv()

app = FastAPI()
API_KEY = os.getenv("API_KEY") #when more cameras are added use the mac address of the camera and a lookup db
NOTIFICATION_TOKEN = os.getenv("NOTIFICATION_TOKEN") #token for the ntfy service
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL") #base url for the ntfy service

class MessageSchema(BaseModel):
    message : str
    topic : str    

@app.get("/list")
async def list_images(x_api_key:str = Header(...)):
    if (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")
    files = os.listdir(UPLOAD_DIR)
    return JSONResponse(content={"files": files}, status_code=200)

@app.get("/get-file/{filename}")
async def get_file(filename: str, x_api_key:str = Header(...)):
    if (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")    
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path)

@app.post("/notification")
async def post_notification(message:MessageSchema, x_api_key:str = Header(...)):    
    if (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")    
    url = NOTIFICATION_URL
    async with httpx.AsyncClient() as client:
        client.headers = {
            "Authorization": f"Bearer {NOTIFICATION_TOKEN}",
            "Tags": "loudspeaker"
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
    file_path = os.path.join(UPLOAD_DIR, new_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)        
    return JSONResponse(content={"f":new_name.name},status_code=201) 


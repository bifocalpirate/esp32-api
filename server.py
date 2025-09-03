from fastapi import FastAPI, File, UploadFile,HTTPException
from fastapi.params import Header
from fastapi.responses import JSONResponse
from typing import List
from dotenv import load_dotenv
import shutil
import os

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
load_dotenv()

app = FastAPI()
API_KEY = os.getenv("API_KEY") #the key was changed from the previously hard-coded value
@app.post("/upload")
async def upload_image(file:UploadFile = File(...), x_api_key:str = Header(...)):
    if (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")
    
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG and PNG are allowed.")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return JSONResponse(content={"filename": file.filename, "status": "uploaded"}, status_code=201)


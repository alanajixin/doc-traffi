from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import uuid

app = FastAPI()

# Temporary storage for content by chat_id
content_store = {}

class UrlRequest(BaseModel):
    url: str

@app.post("/process_url")
async def process_url(request: UrlRequest):
    url = request.url
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")

    # Scrape the web content
    soup = BeautifulSoup(response.content, "html.parser")
    text = soup.get_text(separator=' ', strip=True)
    
    # Create a unique chat_id
    chat_id = str(uuid.uuid4())
    
    # Store the content
    content_store[chat_id] = text
    
    return {"chat_id": chat_id, "message": "URL content processed and stored successfully."}

# 2. Process PDF Document API: 
from fastapi import UploadFile, File, HTTPException
import pdfplumber

@app.post("/process_pdf")
async def process_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a PDF.")
    
    try:
        with pdfplumber.open(file.file) as pdf:
            text = ''.join([page.extract_text() for page in pdf.pages if page.extract_text() is not None])
        text = text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    # Create a unique chat_id
    chat_id = str(uuid.uuid4())
    
    # Store the content
    content_store[chat_id] = text
    
    return {"chat_id": chat_id, "message": "PDF content processed and stored successfully."}


# 3. Create the Chat API

from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

@app.post("/chat")
async def chat(chat_id: str, question: str):
    content = content_store.get(chat_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Chat ID not found.")

    # Embed both the content and the question
    content_embedding = model.encode([content], convert_to_tensor=True)
    question_embedding = model.encode([question], convert_to_tensor=True)
    
    # Compute cosine similarity
    cosine_scores = util.pytorch_cos_sim(question_embedding, content_embedding)
    
    response_index = cosine_scores.argmax().item()
    response_text = content[response_index]
    
    return {"response": response_text}

import threading
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline
import torch
import streamlit as st
import requests
import uvicorn

# -----------------------------
# Load IBM Granite 2B Model
# -----------------------------
MODEL_NAME = "ibm-granite/granite-3.0-2b-instruct"

try:
    generator = pipeline(
        "text-generation",
        model=MODEL_NAME,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )
except Exception as e:
    raise RuntimeError(f"Model load failed: {e}")

# -----------------------------
# FastAPI Backend
# -----------------------------
app = FastAPI(title="Finance Chatbot API")

class ChatRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 200

class ChatResponse(BaseModel):
    response: str

@app.get("/")
def root():
    return {"status": "Finance Chatbot is running 🚀"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    try:
        out = generator(
            req.prompt,
            max_new_tokens=req.max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9
        )
        return ChatResponse(response=out[0]["generated_text"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------
# Streamlit Frontend
# -----------------------------
def run_streamlit():
    st.set_page_config(page_title="Finance Chatbot", page_icon="💰")
    st.title("💰 Finance Chatbot (IBM Granite 2B)")

    user_input = st.text_input("Ask about savings, taxes, or investments:")
    if st.button("Get Answer") and user_input:
        with st.spinner("Thinking..."):
            try:
                res = requests.post(
                    "http://localhost:8000/chat",
                    json={"prompt": user_input, "max_new_tokens": 200},
                    timeout=60
                )
                if res.status_code == 200:
                    st.write("🤖:", res.json()["response"])
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Backend error: {e}")

# -----------------------------
# Run backend & frontend together
# -----------------------------
if __name__ == "__main__":
    # Start FastAPI server in a background thread
    def run_api():
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    # Give backend time to start
    time.sleep(2)
    # Start Streamlit
    run_streamlit()

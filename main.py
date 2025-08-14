from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Backend is running on Railway!"}

# Optional: Simple fake news check placeholder
@app.get("/check")
def check_news(title: str):
    # Dummy response for demo
    return {
        "title": title,
        "credibility_score": 85,
        "status": "Likely Reliable"
    }

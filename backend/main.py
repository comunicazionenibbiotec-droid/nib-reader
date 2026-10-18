from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import ImageRequest

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def root():

    return {
        "status":"online"
    }

@app.post("/analyze")
def analyze(data:ImageRequest):

    return {

        "test_detected": True,

        "valid": True,

        "control_line": False,

        "test_line": False,

        "IC": 0,

        "IT": 0,

        "ratio": 0,

        "result": "demo"

    }
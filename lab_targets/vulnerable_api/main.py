# Placeholder - full implementation in Epoch 1 session 1
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "placeholder - build starts Epoch 1"}

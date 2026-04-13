from fastapi import FastAPI

app = FastAPI()

@app.get("/")

def home():
    return {"message": "CallDesk is running"}

@app.get("/calls")
def home():
    calls = [
        {"caller_number": "(813) 402-9187", "status": "new"},
        {"caller_number": "(727) 554-0023", "status": "assigned"}
    ]
    return calls

@app.get("/calls/summary")
def get_summary():
    return {
        "total": 2,
        "new": 1,
        "assigned": 1
    }
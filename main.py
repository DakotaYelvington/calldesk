from fastapi import FastAPI , HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True)
    caller_number = Column(String)
    status = Column(String)
    assigned_to = Column(String)
    notes = Column(Text)

class NewCall(BaseModel):
    caller_number: str
    status: str = "new"
    assigned_to: str = "unassigned"
    notes: str = ""


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"]
)

@app.get("/calls")
def get_calls():
    db = SessionLocal()
    calls = db.query(CallLog).all()
    db.close()

    return [
        {
            "id": call.id,
            "caller_number": call.caller_number,
            "status": call.status,
            "assigned_to": call.assigned_to,
            "notes": call.notes
        }
        for call in calls
    ]


@app.post("/calls")
def create_call(call: NewCall):
    db = SessionLocal()

    new_call = CallLog(
        caller_number = call.caller_number,
        status = call.status,
        assigned_to = call.assigned_to,
        notes = call.notes
    )

    db.add(new_call)
    db.commit()
    db.close()

    return {"message": "Call saved successfully"}


class AssignCall(BaseModel):
    employee: str



@app.put("/calls/{call_id}/assign")
def assign_call(call_id: int, assignment: AssignCall):
    db = SessionLocal()

    call = db.query(CallLog).filter(CallLog.id == call_id).first()

    if not call:
        db.close()
        raise HTTPException(status_code = 404, detail = "Call not found")
    
    call.assigned_to = assignment.employee
    call.status = "assigned"
    db.commit()
    db.close()

    return {"message": f"Call {call_id} assigned to {assignment.employee}"}


@app.put("/calls/{call_id}/mark-spam")
def mark_spam(call_id: int):
    db = SessionLocal()

    call = db.query(CallLog).filter(CallLog.id == call_id).first()

    if not call:
        db.close()
        raise HTTPException(status_code = 404, detail = "Call not found")
    
    call.status = "spam"
    db.commit()
    db.close()

    return {"message": f"Call {call_id} marked as spam"}


@app.get("/calls/summary")
def get_summary():
    db = SessionLocal()

    total = db.query(CallLog).count()
    
    new = db.query(CallLog).filter(
        CallLog.status == "new"
    ).count()

    assigned = db.query(CallLog).filter(
        CallLog.status == "assigned"
    ).count()

    spam = db.query(CallLog).filter(
        CallLog.status == "spam"
    ).count()

    db.close()

    return {
        "total": total,
        "new": new,
        "assigned": assigned,
        "spam": spam
    }
from fastapi import FastAPI , HTTPException, Form
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

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

class FilteredNumber(Base):
    __tablename__ = "filtered_numbers"

    id = Column(Integer, primary_key=True)
    phone_number = Column(String, unique=True)
    category = Column(String)
    label = Column(String)

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

#------Calls------

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

#------Assign-------

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

#------Mark Spam------

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





#------Incoming Call------

@app.post("/incoming-call")
async def incoming_call(
    From: str = Form(...),
    CallSid: str = Form(...),
    CallStatus: str = Form(...)
):
    db = SessionLocal()
    forward_to = os.getenv("FORWARD_TO")

    twiml_forward = f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>Please hold while we connect your call.</Say><Dial>{forward_to}</Dial></Response>'

    filtered = db.query(FilteredNumber).filter(
        FilteredNumber.phone_number == From
    ).first()

    if filtered and filtered.category == "spam":
        db.close()
        twiml_reject = "<?xml version='1.0' encoding='UTF-8'?><Response><Reject/></Response>"
        return Response(content=twiml_reject, media_type='application/xml')
    
    elif filtered and filtered.category == "personal":
        new_call = CallLog(
            caller_number = From,
            status = "personal",
            assigned_to = "N/A",
            notes = f'Personal call from {filtered.label}'
        )
        db.add(new_call)
        db.commit()
        db.close()
        return Response(content=twiml_forward, media_type="application/xml")
    
    elif filtered and filtered.category == "employee":
        new_call = CallLog(
            caller_number = From,
            status = "employee",
            assigned_to = filtered.label,
            notes = f'Internal call from {filtered.label}'
        )
        db.add(new_call)
        db.commit()
        db.close()
        return Response(content=twiml_forward, media_type="application/xml")
    
    else:
        new_call = CallLog(
            caller_number = From,
            status = "new",
            assigned_to = "unassigned",
            notes = "Incoming call - awaiting assignment"
        )
        db.add(new_call)
        db.commit()
        db.close()
        return Response(content=twiml_forward, media_type="application/xml")
    
#------Filtered Numbers------

@app.get("/filtered_numbers")
def get_filtered_numbers():
    db = SessionLocal()
    numbers = db.query(FilteredNumber).all()
    db.close()
    return [
        {
            "id": n.id,
            "phone_number": n.phone_number,
            "category": n.category,
            "label": n.label
        }
        for n in numbers
    ]

#------Add Filtered Numbers------

@app.post("/filtered-numbers")
def add_filtered_number(phone_number: str, category: str, label: str = ""):
    if category not in ["spam", "personal", "employee"]:
        raise HTTPException(status_code=400, detail="Category must be spam, personal, or employee")
    db = SessionLocal()
    existing = db.query(FilteredNumber).filter(
        FilteredNumber.phone_number == phone_number
    ).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Number already exists")
    new_number = FilteredNumber(
        phone_number=phone_number,
        category=category,
        label=label
    )
    db.add(new_number)
    db.commit()
    db.close()
    return {"message": f"{phone_number} added as {category}"}

#------Delete Filtered Number------
@app.delete("/filtered-numbers/{number_id}")
def delete_filtered_number(number_id: int):
    db = SessionLocal()
    number = db.query(FilteredNumber).filter(
        FilteredNumber.id == number_id
    ).first()
    if not number:
        db.close()
        raise HTTPException(status_code=404, detail="Number not found")
    db.delete(number)
    db.commit()
    db.close()
    return {"message": "Number removed"}
#------Call Summary------

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


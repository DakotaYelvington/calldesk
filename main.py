from fastapi import FastAPI , HTTPException, Form, Header, Depends
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv
from twilio.rest import Client
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
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

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    api_key = os.getenv("API_KEY")
    if x_api_key != api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
def get_current_user(x_token: Optional[str] = Header(None)):
    if not x_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_token(x_token)


app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"]
)

#------Calls------

@app.get("/calls")
@limiter.limit("30/minute")
def get_calls(request: Request, username: str = Depends(get_current_user)):
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
def assign_call(call_id: int, assignment: AssignCall, username: str = Depends(get_current_user)):
    db = SessionLocal()

    call = db.query(CallLog).filter(CallLog.id == call_id).first()
    if not call:
        db.close()
        raise HTTPException(status_code=404, detail="Call not found")

    call.assigned_to = assignment.employee
    call.status = "assigned"
    db.commit()

    employee = db.query(Employee).filter(
        Employee.full_name == assignment.employee,
        Employee.is_active == True
    ).first()

    if employee:
        try:
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

            client = Client(account_sid, auth_token)
            client.messages.create(
                body=f"New job assigned to you!\nCaller: {call.caller_number}\nNotes: {call.notes}\nCheck the app for details.",
                from_=twilio_number,
                to=employee.phone_number
            )
            print(f"SMS sent to {employee.full_name} at {employee.phone_number}")
        except Exception as e:
            print(f"SMS failed: {e}")

    db.close()
    return {"message": f"Call {call_id} assigned to {assignment.employee}"}

#------Mark Spam------

@app.put("/calls/{call_id}/mark-spam")
def mark_spam(call_id: int, username: str = Depends(get_current_user)):
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
def get_filtered_numbers(username: str = Depends(get_current_user)):
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
def add_filtered_number(phone_number: str, category: str, label: str = "", username: str = Depends(get_current_user)):
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
def delete_filtered_number(number_id: int, username: str = Depends(get_current_user)):
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

#------Employee------
class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    full_name = Column(String)
    phone_number = Column(String)
    is_active = Column(Boolean, default=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    business_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(String)


@app.get("/employees")
def get_employees(username: str = Depends(get_current_user)):
    db = SessionLocal()
    employees = db.query(Employee).filter(
        Employee.is_active == True
    ).all()
    db.close()
    return [
        {
            "id": e.id,
            "full_name": e.full_name,
            "phone_number": e.phone_number
        }
        for e in employees
    ]

@app.post("/employees")
def add_employee(full_name: str, phone_number: str, username: str = Depends(get_current_user)):
    db = SessionLocal()
    new_employee = Employee(
        full_name=full_name,
        phone_number=phone_number
    )
    db.add(new_employee)
    db.commit()
    db.close()
    return {"message": f"{full_name} added successfully"}

#------Call Summary------

@app.get("/calls/summary")
def get_summary(username: str = Depends(get_current_user)):
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
class UserRegister(BaseModel):
    username: str
    password: str
    business_name: str

class UserLogin(BaseModel):
    username: str
    password: str


#------Register------
@app.post("/register")
def register(user: UserRegister):
    db = SessionLocal()

    existing = db.query(User).filter(
        User.username == user.username
    ).first()

    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Username is already taken")
    
    new_user = User(
        username=user.username,
        hashed_password=hash_password(user.password),
        business_name=user.business_name
    )

    db.add(new_user)
    db.commit()
    db.close()

    return {"message": "Account created successfully"}

#------Login------

@app.post("/login")
def login(user: UserLogin):
    db = SessionLocal()
    existing = db.query(User).filter(
        User.username == user.username
    ).first()
    if not existing or not verify_password(user.password, existing.hashed_password):
        db.close()
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    db.close()

    token = create_token({"sub": existing.username})
    return {
        "token": token,
        "username": existing.username,
        "business_name": existing.business_name
    }
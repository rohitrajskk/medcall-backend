from typing import Optional
from typing import List
from fastapi import FastAPI
import server.database as database
from pydantic import BaseModel
from enum import Enum

app = FastAPI()
class Patient(BaseModel):
    name: str
    mobile_no: int
    age: int
    relationship: Optional[str]
    gender: str
    pre_existing_medical_condition: List[str] = None

class vital(BaseModel):
    body_temperature: float
    pulse_rate: int
    respiration_rate: int
    blood_pressure: int
    blood_sugar: int

class medicine(BaseModel):
    name: str
    frequency: float
    treatment_period: int

class prescription(BaseModel):
    diagnosis: Optional[str]
    medicines: List[medicine]
    referal_doc_id: Optional[str]
    consulting_doc_id: str
    follow_up_date: Optional[int]
    instructions: Optional[str]

class appointment(BaseModel):
    vitals: vital
    patient_id: str


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to this fantastic app!"}

@app.get("/patient/{id}", tags=["Root"])
async def get_patients(id):
    #return {"message": "Return patients"}
    patients = await database.get_patient(patient_id=id)
    print(patients)
    if patients:
        return patients
    else:
        return {"message": "No patients found in the database"}

@app.get("/patient", tags=["Root"])
async def get_patients(mobile_no: Optional[int] = None):
    #return {"message": "Return patients"}
    patients = await database.get_patient(mobile_no=mobile_no)
    print(patients)
    if patients:
        return patients
    else:
        return {"message": "No patients found in the database"}

@app.post("/patient", tags=["Root"], )
async def add_patients(patient: Patient):
    new_patient  = await database.add_patient(patient.dict())
    return { "patient_id": str(new_patient.inserted_id), "message": "Sucessfully added patient"}

@app.get("/patient/{id}/appointment/{appointment_id}", tags=["Root"])
async def get_appointments(id, appointment_id):
    #return {"message": "Return patients"}
    appointment = await database.get_appointment(patient_id=id, appointment_id=appointment_id)
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}

@app.get("/patient/{id}/appointment", tags=["Root"])
async def get_appointments(id):
    #return {"message": "Return patients"}
    appointment = await database.get_appointment(patient_id=id)
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}

@app.post("/patient/{id}/appointment", tags=["Root"])
async def create_appointment(id, appointment: vital):
    new_appointment = await database.create_appointment(patient_id=id, vital=appointment.dict())
    if new_appointment is not None:
        print(new_appointment)
        return { "patient_id": str(new_appointment.inserted_id), "message": "Sucessfully added patient"}
    else:
        return { "message": "Parent ID: {} not found in database".format(id)}

@app.get("/active/appointment", tags=["Root"])
async def get_appointments():
    #return {"message": "Return patients"}
    appointment = await database.active_appointment()
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}

@app.get("/inactive/appointment", tags=["Root"])
async def get_appointments():
    #return {"message": "Return patients"}
    appointment = await database.inactive_appointment()
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}

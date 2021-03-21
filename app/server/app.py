from typing import Optional
from typing import List
from fastapi import FastAPI
import server.database as database
from pydantic import BaseModel
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "*"
]
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.staticfiles import StaticFiles
app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )
class Patient(BaseModel):
    name: str
    mobile_no: int
    age: int
    relationship: Optional[str]
    gender: str
    pre_existing_medical_condition: List[str] = None

class DoctorType(Enum):
    INHOUSE = 1
    EXTERNAL = 2

class address(BaseModel):
        name: str
        mobile_no: int
        pincode: int
        landmark : str
        address_str: str
        city: str
        state: str
        google_map: str

class doctor(BaseModel):
    mobile_no: int
    alternate_mobile_no: Optional[int]
    doctor_name: str
    availibility: DoctorType
    degree: str
    specilisation: str
    registration_no: Optional[str]
    consultation_fee: int
    rating: float
    doctor_address: address
    service_timing_week: Optional[str]
    service_timing_day: Optional[str]

class vital(BaseModel):
    body_temperature: float
    pulse_rate: int
    respiration_rate: int
    blood_pressure_sys: int
    blood_pressure_dia: int
    blood_sugar: int

class medicine(BaseModel):
    medicine_name: str
    brand_name: str
    medicine_mg: str
    treatment_gap_day: Optional[int]
    treatment_time: List[str]
    treatment_food_dependecy: Optional[str]
    treatment_instruction: Optional[str]
    treatment_period: int



class test(BaseModel):
    test_name: str
    lab_name: Optional[str]
    lab_address: address
    test_comment: str

class prescription(BaseModel):
    diagnosis: Optional[str]
    medicines: List[medicine]
    test: Optional[test]
    referal_doc_id: Optional[doctor]
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
        return { "appointment_id": str(new_appointment.inserted_id), "message": "Sucessfully added patient"}
    else:
        return { "message": "Parent ID: {} not found in database".format(id)}

@app.post("/patient/{id}/appointment/{appointment_id}/prescription", tags=["Root"])
async def add_prescription(id, appointment_id, prescription: prescription):
    #return {"message": "Return patients"}
    appointment = await database.add_prescription(patient_id=id, appointment_id=appointment_id, prescription=prescription)
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}

@app.get("/patient/{id}/appointment/{appointment_id}/prescription", tags=["Root"])
async def get_prescription(id, appointment_id):
    #return {"message": "Return patients"}
    appointment = await database.get_appointment(patient_id=id, appointment_id=appointment_id)
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}

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

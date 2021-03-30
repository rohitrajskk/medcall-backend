from typing import Optional
from typing import List
from fastapi import FastAPI
import server.database as database
from server.database import DoctorType
from pydantic import BaseModel
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.staticfiles import StaticFiles

origins = [
    "*"
]

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


class Address(BaseModel):
    name: Optional[str]
    mobile_no: Optional[int]
    pin_code: Optional[int]
    landmark: Optional[str]
    address_str: Optional[str]
    city: Optional[str]
    state: Optional[str]
    google_map: Optional[str]


class Doctor(BaseModel):
    mobile_no: int
    alternate_mobile_no: Optional[int]
    doctor_name: str
    availability: DoctorType
    degree: str
    specialisation: str
    registration_no: Optional[str]
    consultation_fee: int
    rating: Optional[float]
    doctor_address: Optional[Address]
    service_timing_week: Optional[str]
    service_timing_day: Optional[str]
    experience: Optional[int]

    class Config:
        use_enum_values = True


class MedicalShop(BaseModel):
    mobile_no: int
    alternate_mobile_no: Optional[int]
    medical_shop_name: str
    registration_no: Optional[str]
    rating: Optional[float]
    medical_shop_address: Address


class Vital(BaseModel):
    body_temperature: float
    pulse_rate: int
    respiration_rate: int
    blood_pressure_sys: int
    blood_pressure_dia: int
    blood_sugar: int


class Medicine(BaseModel):
    medicine_name: str
    brand_name: str
    medicine_mg: str
    treatment_gap_day: Optional[int]
    treatment_time: List[str]
    treatment_food_dependency: Optional[str]
    treatment_instruction: Optional[str]
    treatment_period: int


class Test(BaseModel):
    test_name: str
    lab_name: Optional[str]
    lab_address: Optional[Address]
    test_comment: Optional[str]


class Prescription(BaseModel):
    diagnosis: Optional[str]
    medicines: List[Medicine]
    test: Optional[List[Test]]
    follow_up_date: Optional[int]
    instructions: Optional[str]


class Appointment(BaseModel):
    vitals: Vital
    patient_id: str


class ReferralDoctor(BaseModel):
    referral_doc_id: str


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to this fantastic app!"}


@app.get("/patient/{patient_id}", tags=["Root"])
async def get_patients(patient_id):
    # return {"message": "Return patients"}
    patients = await database.get_patient(patient_id=patient_id)
    # print(patients)
    if patients:
        return patients
    else:
        return {"message": "No patients found in the database"}


@app.get("/patient", tags=["Root"])
async def get_patients(mobile_no: Optional[int] = None):
    # return {"message": "Return patients"}
    patients = await database.get_patient(mobile_no=mobile_no)
    # print(patients)
    if patients:
        return patients
    else:
        return {"message": "No patients found in the database"}


@app.post("/patient", tags=["Root"], )
async def add_patients(patient: Patient):
    new_patient = await database.add_patient(patient.dict())
    return {"patient_id": str(new_patient.inserted_id), "message": "Successfully added patient"}


@app.get("/doctor/external", tags=["Root"])
async def get_external_doctor():
    doctors = await database.get_external_doctor()
    if doctors:
        return doctors
    else:
        return {"message": "No doctors found in the database"}


@app.get("/doctor/{doctor_id}", tags=["Root"])
async def get_doctor(doctor_id):
    doctor = await database.get_doctor(doctor_id=doctor_id)
    if doctor:
        return doctor
    else:
        return {"message": "No doctor with ID; {} found in the database".format(doctor_id)}


@app.get("/doctor", tags=["Root"])
async def get_doctor(mobile_no: Optional[int] = None):
    doctors = await database.get_doctor(mobile_no=mobile_no)
    if doctors:
        return doctors
    else:
        return {"message": "No doctors found in the database"}


@app.post("/doctor", tags=["Root"], )
async def add_doctor(doctor: Doctor):
    new_doctor = await database.add_doctor(doctor.dict())
    return {"doctor_id": str(new_doctor.inserted_id), "message": "Successfully added doctor"}


@app.get("/medical-shop/{shop_id}", tags=["Root"])
async def get_medical_shop(shop_id):
    medical_shop = await database.get_medical_shop(shop_id=shop_id)
    if medical_shop:
        return medical_shop
    else:
        return {"message": "No medical shop with ID; {} found in the database".format(shop_id)}


@app.get("/medical-shop", tags=["Root"])
async def get_medical_shop(mobile_no: Optional[int] = None):
    medical_shop = await database.get_medical_shop(mobile_no=mobile_no)
    if medical_shop:
        return medical_shop
    else:
        return {"message": "No medical shop found in the database"}


@app.post("/medical-shop", tags=["Root"], )
async def add_medical_shop(medical_shop: MedicalShop):
    new_medical_shop = await database.add_medical_shop(medical_shop.dict())
    return {"doctor_id": str(new_medical_shop.inserted_id), "message": "Successfully added medical shop"}


@app.get("/patient/{patient_id}/appointment/{appointment_id}", tags=["Root"])
async def get_appointments(patient_id, appointment_id):
    # return {"message": "Return patients"}
    appointment = await database.get_appointment(patient_id=patient_id, appointment_id=appointment_id)
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}


@app.get("/patient/{patient_id}/appointment", tags=["Root"])
async def get_appointments(patient_id):
    # return {"message": "Return patients"}
    appointment = await database.get_appointment(patient_id=patient_id)
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}


@app.post("/patient/{patient_id}/appointment", tags=["Root"])
async def create_appointment(patient_id, appointment: Vital):
    new_appointment = await database.create_appointment(patient_id=patient_id, vital=appointment.dict())
    if new_appointment is not None:
        # print(new_appointment)
        return {"appointment_id": str(new_appointment.inserted_id), "message": "Successfully added patient"}
    else:
        return {"message": "Parent ID: {} not found in database".format(patient_id)}


@app.post("/patient/{patient_id}/appointment/{appointment_id}/prescription", tags=["Root"])
async def add_prescription(patient_id, appointment_id, prescription: Prescription):
    # return {"message": "Return patients"}
    new_prescription = await database.add_appointment_prescription(prescription=prescription.dict(),
                                                                   patient_id=patient_id, appointment_id=appointment_id)
    if new_prescription:
        return {"_id": appointment_id, "message": "Successfully updated prescription"}
    else:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}


@app.get("/patient/{patient_id}/appointment/{appointment_id}/prescription", tags=["Root"])
async def get_prescription(patient_id, appointment_id):
    appointment = await database.get_appointment(patient_id=patient_id, appointment_id=appointment_id)
    if appointment is None:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}
    elif appointment.get("prescription"):
        return appointment.get("prescription")
    else:
        return {"message": "No prescription found in the database"}


@app.post("/patient/{patient_id}/appointment/{appointment_id}/referral", tags=["Root"])
async def add_referral(patient_id, appointment_id, referral: ReferralDoctor):
    new_referral = await database.add_appointment_referral(patient_id=patient_id, appointment_id=appointment_id,
                                                           referral_doctor=referral.dict())
    if new_referral:
        return {"_id": appointment_id, "message": "Successfully updated referral"}
    else:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}


@app.get("/patient/{patient_id}/appointment/{appointment_id}/referral", tags=["Root"])
async def get_referral(patient_id, appointment_id):
    appointment = await database.get_appointment(patient_id=patient_id, appointment_id=appointment_id)
    if appointment is None:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}
    elif appointment.get("referral"):
        doctor = await database.get_doctor(doctor_id=appointment.get("referral"))
        return doctor
    else:
        return {"message": "No referral found in the database"}


@app.get("/active/appointment", tags=["Root"])
async def get_appointments():
    # return {"message": "Return patients"}
    appointment = await database.active_appointment()
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}


@app.get("/inactive/appointment", tags=["Root"])
async def get_appointments():
    # return {"message": "Return patients"}
    appointment = await database.inactive_appointment()
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}

import motor.motor_asyncio
from bson.objectid import ObjectId
import pymongo
from datetime import datetime
from enum import Enum

class DocType(Enum):
    FAMILY_USER = 1
    PATIENT_USER = 2
    APPOINTMENT = 3

class AppointmentStatus(Enum):
    CREATED = 1
    IN_QUEUE = 2
    VIDEO_CALL = 3
    COMPLETED = 4

MONGO_DETAILS = "mongodb://localhost:27017"

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

database = client.patients

patient_collection = database.get_collection("patient_collection6")
patient_collection.create_index("parent")
patient_collection.create_index("doc_type")
patient_collection.create_index([("mobile_no", pymongo.DESCENDING), ("name", pymongo.DESCENDING), ("doc_type", pymongo.DESCENDING), ("time", pymongo.DESCENDING)], unique=True)

async def get_patient(patient_id=None, mobile_no=None):
    if patient_id:
        patient = await patient_collection.find_one({"_id": ObjectId(patient_id)})
        if patient:
            return patient_helper(patient)
        return None
    elif mobile_no:
        patients = []
        parent_user = await patient_collection.find_one({"mobile_no": mobile_no, "parent": None})
        async for patient in patient_collection.find({"parent": str(parent_user["_id"])}):
            patients.append(patient_helper(patient))
    else:
        patients = []
        async for patient in patient_collection.find():
            patients.append(patient_helper(patient))

    return patients

# Add a new patient into to the database
async def add_patient(patient_data: dict) -> dict:
    parent_user = await patient_collection.find_one({"mobile_no": patient_data["mobile_no"], "parent": None})
    #print(parent_user)
    if not parent_user:
        patient = await patient_collection.insert_one({"mobile_no": patient_data["mobile_no"], "doc_type": DocType.FAMILY_USER.value})
        #print(patient)
        patient_data["parent"] = str(patient.inserted_id)
        patient_data["doc_type"] = DocType.PATIENT_USER.value
        new_patient = await patient_collection.insert_one(patient_data)
    else:
        patient_data["parent"] = str(parent_user["_id"])
        patient_data["doc_type"] = DocType.PATIENT_USER.value
        new_patient = await patient_collection.insert_one(patient_data)
    return new_patient




async def create_appointment(patient_id, vital: dict):
    patient = await patient_collection.find_one({"_id": ObjectId(patient_id)})
    if patient is None:
        return None
    appointment = dict()
    appointment["vital"] = vital
    appointment["parent"] = patient_id
    appointment["time"] = datetime.now()
    appointment["doc_type"] = DocType.APPOINTMENT.value
    appointment["status"] = AppointmentStatus.CREATED.value
    appointment["is_active"] = True
    new_appointment = await patient_collection.insert_one(appointment)
    print(new_appointment)
    return new_appointment

async def get_appointment(patient_id, appointment_id=None):
    if appointment_id is None:
        appointments = []
        async for patient in patient_collection.find({"parent": patient_id}):
            appointments.append(patient_helper(patient))
        return appointments
    else:
        appointment = await patient_collection.find_one({"_id": ObjectId(appointment_id)})
        return patient_helper(appointment)

async def active_appointment():
    appointments = []
    async for patient in patient_collection.find({"doc_type": 3, "status": {"$ne": AppointmentStatus.COMPLETED.value}}):
        appointments.append(patient_helper(patient))
    return appointments


async def inactive_appointment():
    appointments = []
    async for patient in patient_collection.find({"doc_type": 3, "status": AppointmentStatus.COMPLETED.value}):
        appointments.append(patient_helper(patient))
    return appointments


def patient_helper(patient) -> dict:
    #print(patient)
    patient["_id"] = str(patient["_id"])
    return patient

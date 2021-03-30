import motor.motor_asyncio
from bson.objectid import ObjectId
import pymongo
from datetime import datetime
from enum import Enum
import server.daily_co_meeting as meeting


class DocType(Enum):
    FAMILY_USER = 1
    PATIENT_USER = 2
    APPOINTMENT = 3


class UserRole(str, Enum):
    doctor = 'doctor'
    medical_shop = 'medical_shop'
    patient = 'patient'


class AppointmentStatus(Enum):
    CREATED = 1
    IN_QUEUE = 2
    VIDEO_CALL = 3
    COMPLETED = 4


class DoctorType(Enum):
    INHOUSE = 1
    EXTERNAL = 2


MONGO_DETAILS = "mongodb://localhost:27017"

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

database = client.patients

patient_collection = database.get_collection("patient_collection8")
patient_collection.create_index("parent")
patient_collection.create_index("doc_type")
patient_collection.create_index(
    [("mobile_no", pymongo.DESCENDING), ("name", pymongo.DESCENDING), ("doc_type", pymongo.DESCENDING),
     ("time", pymongo.DESCENDING)], unique=True)

doctor_collection = database.get_collection("doctor_collection1")
doctor_collection.create_index("availability")
doctor_collection.create_index([("mobile_no", pymongo.DESCENDING)], unique=True)

medical_shop_collection = database.get_collection("medical_shop_collection")
medical_shop_collection.create_index([("mobile_no", pymongo.DESCENDING)], unique=True)


user_db = database.get_collection("user_collection")
user_db.create_index("username", unique=True)
user_db.create_index("mobile_no", unique=True)


async def get_user(username=None, mobile_no=None):
    if username:
        user = await user_db.find_one({"username": username})
        if user:
            return patient_helper(user)
        else:
            None
    elif mobile_no:
        user = await user_db.find_one({"mobile_no": mobile_no})
        if user:
            return patient_helper(user)
        else:
            return None


async def create_user(user: dict):
    new_user = await user_db.insert_one(user)
    return new_user


async def update_user(username: str, user_data: dict):
    result = await user_db.update_one({"username": username},
                                             {"$set": {"user_data": user_data}})
    if result.modified_count == 1:
        return True
    else:
        return False


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
    # print(parent_user)
    if not parent_user:
        patient = await patient_collection.insert_one(
            {"mobile_no": patient_data["mobile_no"], "doc_type": DocType.FAMILY_USER.value, "user_role": UserRole.PATIENT.value})
        # print(patient)
        patient_data["parent"] = str(patient.inserted_id)
        patient_data["doc_type"] = DocType.PATIENT_USER.value
        patient_data["user_role"] = UserRole.PATIENT.value
        new_patient = await patient_collection.insert_one(patient_data)
    else:
        patient_data["parent"] = str(parent_user["_id"])
        patient_data["doc_type"] = DocType.PATIENT_USER.value
        patient_data["user_role"] = UserRole.PATIENT.value
        new_patient = await patient_collection.insert_one(patient_data)
    return new_patient


async def get_doctor(doctor_id=None, mobile_no=None):
    if doctor_id:
        doctor = await doctor_collection.find_one({"_id": ObjectId(doctor_id)})
        if doctor:
            return patient_helper(doctor)
        return None
    elif mobile_no:
        doctor = await patient_collection.find_one({"mobile_no": mobile_no})
        if doctor:
            return patient_helper(doctor)
        return None
    else:
        doctors = []
        async for doctor in doctor_collection.find():
            doctors.append(patient_helper(doctor))
        return doctors


async def get_external_doctor(doctor_id=None, mobile_no=None):
    doctors = []
    async for doctor in doctor_collection.find({"availability": DoctorType.EXTERNAL.value}):
        doctors.append(patient_helper(doctor))
    return doctors


async def add_doctor(doctor_data: dict) -> dict:
    doctor_data["user_role"] = UserRole.DOCTOR.value
    print(doctor_data)
    new_doctor = await doctor_collection.insert_one(doctor_data)
    return new_doctor


async def get_medical_shop(shop_id=None, mobile_no=None):
    if shop_id:
        shop = await medical_shop_collection.find_one({"_id": ObjectId(shop_id)})
        if shop:
            return patient_helper(shop)
        return None
    elif mobile_no:
        shop = await medical_shop_collection.find_one({"mobile_no": mobile_no})
        if shop:
            return patient_helper(shop)
        return None
    else:
        shops = []
        async for shop in medical_shop_collection.find():
            shops.append(patient_helper(shop))
        return shops


async def add_medical_shop(shop_data: dict) -> dict:
    shop_data["user_role"] = UserRole.MEDICALSHOP.value
    new_shop = await medical_shop_collection.insert_one(shop_data)
    return new_shop


async def create_appointment(patient_id, vital: dict):
    patient = await patient_collection.find_one({"_id": ObjectId(patient_id)})
    if patient is None:
        return None
    appointment = dict()
    appointment["patient"] = patient_helper(patient)
    appointment["vital"] = vital
    appointment["parent"] = patient_id
    appointment["time"] = datetime.now()
    appointment["doc_type"] = DocType.APPOINTMENT.value
    appointment["status"] = AppointmentStatus.CREATED.value
    appointment["is_active"] = True
    daily_co_meeting = meeting.getmeetings(patient_id=patient_id)
    appointment["meeting"] = {
        "doctor_meeting_url": daily_co_meeting["url"],
        "patient_meeting_url": daily_co_meeting["url"],
        "meeting_id": daily_co_meeting["id"]
    }
    appointment["prescription"] = None
    appointment["referral"] = None
    new_appointment = await patient_collection.insert_one(appointment)
    # print(new_appointment)
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


async def add_appointment_prescription(prescription: dict, patient_id=None, appointment_id=None):
    """
    :type prescription: object
    :param appointment_id:
    :param patient_id:
    """
    if appointment_id is None:
        return None
    else:
        result = await patient_collection.update_one({"_id": ObjectId(appointment_id)},
                                                     {"$set": {"prescription": prescription}})
        if result.modified_count == 1:
            return appointment_id
        else:
            return None


async def add_appointment_referral(referral_doctor: dict, patient_id=None, appointment_id=None):
    """
    :type referral_doctor: object
    :param appointment_id:
    :param patient_id:
    """
    if appointment_id is None:
        return None
    else:
        result = await patient_collection.update_one({"_id": ObjectId(appointment_id)},
                                                     {"$set": {"referral": referral_doctor.get("referral_doc_id")}})
        if result.modified_count == 1:
            return appointment_id
        else:
            return None


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
    # print(patient)
    patient["_id"] = str(patient["_id"])
    if patient.get("user_role"):
        patient["user_role"] = UserRole(patient.get("user_role")).name
    return patient

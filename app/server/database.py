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
    admin = 'admin'


class AppointmentStatus(str, Enum):
    CREATED = "created"
    IN_QUEUE = 'in_queue'
    VIDEO_CALL = 'video_call'
    COMPLETED = 'completed'


class DoctorType(Enum):
    INHOUSE = 1
    EXTERNAL = 2


MONGO_DETAILS = "mongodb://localhost:27017"

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

database = client.patients

patient_collection = database.get_collection("patient_collection17")
patient_collection.create_index("parent")
patient_collection.create_index("doc_type")
patient_collection.create_index(
    [("mobile_no", pymongo.DESCENDING), ("name", pymongo.DESCENDING), ("doc_type", pymongo.DESCENDING),
     ("time", pymongo.ASCENDING)], unique=True)

doctor_external_collection = database.get_collection("doctor_collection3")
doctor_external_collection.create_index("specialisation")
doctor_external_collection.create_index([("mobile_no", pymongo.DESCENDING)], unique=True)

medical_test_db = database.get_collection("medical_test")
medical_test_db.create_index("test_name", unique=True)

pre_existing_disease_db = database.get_collection("pre_existing_disease1")
pre_existing_disease_db.create_index("disease_name", unique=True)

medicine_db = database.get_collection("medicine_collection")
medicine_db.create_index([("medicine_name", pymongo.DESCENDING)], unique=True)

user_db = database.get_collection("user_collection1")
user_db.create_index("username", unique=True)
user_db.create_index("mobile_no", unique=True)
user_db.create_index("user_role")


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


async def assign_doctor():
    doctors = user_db.find({"user_role": UserRole.doctor.value}).sort("medical_shop_service_count", 1).limit(1)
    if not doctors:
        return None
    else:
        doctor = (await doctors.to_list(length=1))[0]
        result = await user_db.update_one({"_id": doctor["_id"]},
                                          {"$set": {
                                              "medical_shop_service_count": doctor["medical_shop_service_count"] + 1}})
        if result.modified_count == 1:
            return doctor["username"]
        else:
            return None


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
            {"mobile_no": patient_data["mobile_no"], "doc_type": DocType.FAMILY_USER.value,
             "user_role": UserRole.patient.value})
        # print(patient)
        patient_data["parent"] = str(patient.inserted_id)
        patient_data["doc_type"] = DocType.PATIENT_USER.value
        patient_data["user_role"] = UserRole.patient.value
        new_patient = await patient_collection.insert_one(patient_data)
    else:
        patient_data["parent"] = str(parent_user["_id"])
        patient_data["doc_type"] = DocType.PATIENT_USER.value
        patient_data["user_role"] = UserRole.patient.value
        new_patient = await patient_collection.insert_one(patient_data)
    return new_patient


async def get_external_doctor(doctor_id=None, mobile_no=None, specialisation=None):
    if doctor_id:
        doctor = await doctor_external_collection.find_one({"_id": ObjectId(doctor_id)})
        if doctor:
            return patient_helper(doctor)
        return None
    elif mobile_no:
        doctor = await patient_collection.find_one({"mobile_no": mobile_no})
        if doctor:
            return patient_helper(doctor)
        return None
    elif specialisation:
        doctors = []
        async for doctor in doctor_external_collection.find({"specialisation": specialisation}):
            doctors.append(patient_helper(doctor))
        return doctors
    else:
        doctors = []
        async for doctor in doctor_external_collection.find():
            doctors.append(patient_helper(doctor))
        return doctors


async def add_doctor(doctor_data: dict) -> dict:
    doctor_data["user_role"] = UserRole.doctor.value
    new_doctor = await doctor_external_collection.insert_one(doctor_data)
    return new_doctor


async def get_medicine(medicine_name=None, medicine_id=None):
    if medicine_name:
        medicine_name = await medicine_db.find_one({"medicine_name": medicine_name})
        if medicine_name:
            return patient_helper(medicine_name)
        return None
    elif medicine_id:
        medicine_name = await medicine_db.find_one({"_id": ObjectId(medicine_id)})
        if medicine_name:
            return patient_helper(medicine_name)
        return None
    else:
        medicines = []
        async for medicine in medicine_db.find():
            medicines.append(patient_helper(medicine))
        return medicines


async def add_medicine(medicine: dict):
    new_medicine = await medicine_db.insert_one(medicine)
    return new_medicine


async def create_appointment(patient_id, in_app: dict):
    patient = await patient_collection.find_one({"_id": ObjectId(patient_id)})
    if patient is None:
        return None
    appointment = dict()
    appointment["patient"] = patient_helper(patient)
    appointment["medical_shop_id"] = in_app.pop("medical_shop_id")
    appointment["vital"] = in_app
    appointment["parent"] = patient_id
    appointment["time"] = datetime.utcnow().timestamp()
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


async def update_appointment_status(status: AppointmentStatus, patient_id=None, appointment_id=None):
    """
    :type status: object
    :param appointment_id:
    :param patient_id:
    """
    if appointment_id is None:
        return None
    else:
        result = await patient_collection.update_one({"_id": ObjectId(appointment_id)},
                                                     {"$set": {"status": status}})
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
    return patient


async def get_medical_test(test_name=None):
    if test_name:
        test = await medical_test_db.find_one({"test_name": test_name})
        if test:
            return patient_helper(test)
        return None
    else:
        tests = []
        async for test in medical_test_db.find():
            tests.append(patient_helper(test))
        return tests


async def add_medical_test(test_data: dict) -> dict:
    new_test = await medical_test_db.insert_one(test_data)
    return new_test


async def get_pre_existing_disease(disease_name=None):
    if disease_name:
        disease = await pre_existing_disease_db.find_one({"disease_name": disease_name})
        if disease:
            return patient_helper(disease)
        return None
    else:
        diseases = []
        async for disease in pre_existing_disease_db.find():
            diseases.append(patient_helper(disease))
        return diseases


async def add_pre_existing_disease(disease: dict) -> dict:
    print(disease)
    new_disease = await pre_existing_disease_db.insert_one(disease)
    return new_disease


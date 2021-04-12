from typing import Optional
from typing import List
import server.database as database
from server.database import DoctorType
from server.database import UserRole
from server.database import AppointmentStatus
from pydantic import BaseModel
from pydantic.types import constr
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        self.active_connections = dict()

    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        print(self.active_connections)

    def disconnect(self, connection_id: str):
        self.active_connections.pop(connection_id)
        print(self.active_connections)

    async def send_json(self, message: dict, connection_id: str):
        if self.active_connections.get(connection_id) is not None:
            await self.active_connections[connection_id].send_json(message)


manager = ConnectionManager()

origins = [
    "*"
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "b420ba2c7ca511ff976a51f38e146f2c9bbf8cfa5d0ff3e9097cee3bb5426772"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: UserRole


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: Optional[str]
    mobile_no: int
    email: Optional[str] = None
    full_name: str
    user_role: UserRole
    password: constr(min_length=7, max_length=100)

    class Config:
        use_enum_values = True


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str):
    user = await database.get_user(username=username)
    if not user:
        user = await database.get_user(mobile_no=username)
        if not user:
            return False
        return False
    if not verify_password(password, user["password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = await database.get_user(username=token_data.username)
    # print(user)
    if user is None:
        raise credentials_exception
    return user


class Patient(BaseModel):
    name: str
    mobile_no: int
    age: int
    relationship: Optional[str]
    gender: str
    pre_existing_medical_condition: List[str] = None


class Address(BaseModel):
    name: Optional[str]
    pin_code: Optional[int]
    landmark: Optional[str]
    address_str: Optional[str]
    city: Optional[str]
    state: Optional[str]
    google_map: Optional[str]


class Doctor(BaseModel):
    alternate_mobile_no: Optional[int]
    doctor_name: str
    degree: Optional[str]
    specialisation: str
    registration_no: Optional[str]
    consultation_fee: int
    rating: Optional[float]
    doctor_address: Optional[str]
    service_timing: Optional[str]
    experience: Optional[int]
    associated_hospital: Optional[str]

    class Config:
        use_enum_values = True


class ExternalDoctor(Doctor):
    mobile_no: int


class MedicalShop(BaseModel):
    alternate_mobile_no: Optional[int]
    medical_shop_name: str
    registration_no: Optional[str]
    rating: Optional[float]
    medical_shop_address: Optional[Address]


class Vital(BaseModel):
    body_temperature: float
    pulse_rate: int
    respiration_rate: int
    blood_pressure_sys: int
    blood_pressure_dia: int
    blood_sugar: int


class Medicine(BaseModel):
    medicine_name: str
    brand_name: Optional[List[str]]
    medicine_variety: Optional[List[str]]
    medicine_type: str
    medicine_uses: Optional[str]
    prescription_required: Optional[bool]


class MedicineTreatment(BaseModel):
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
    test_uses: Optional[str]
    test_required_symptom: Optional[str]


class PreExistingDisease(BaseModel):
    disease_name: str


class Prescription(BaseModel):
    diagnosis: Optional[str]
    medicines: List[MedicineTreatment]
    test: Optional[List[Test]]
    follow_up_date: Optional[int]
    instructions: Optional[str]


class Appointment(BaseModel):
    vitals: Vital
    medical_shop_id: str


class ReferralDoctor(BaseModel):
    referral_doc_id: str


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to this fantastic app!"}


@app.post("/user", tags=["Root"])
async def create_user(user: User, response: Response, current_user: dict = Depends(get_current_user)):
    if current_user.get('user_role') != UserRole.admin.value:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {"Only admin is allowed to create new user"}
    old_user = await database.get_user(username=user.username, mobile_no=user.mobile_no)
    if old_user:
        response.status_code = status.HTTP_409_CONFLICT
        return {"User already exist"}
    else:
        new_user = user.dict()
        new_user["password"] = get_password_hash(user.password)
        if user.username is None:
            new_user["username"] = str(user.mobile_no)
            user.username = str(user.mobile_no)
        if user.user_role is UserRole.doctor.value:
            new_user["medical_shop_service_count"] = 0
        elif user.user_role is UserRole.medical_shop.value:
            doctor = await database.assign_doctor()
            if not doctor:
                doctor_assignment_failed = True
            else:
                new_user["assigned_doctor"] = doctor
        new_user_db = await database.create_user(new_user)
        if new_user_db.inserted_id:
            return {"New user with id {} added successfully".format(new_user_db.inserted_id)}
            # Assign a doctor
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"Failed to create user please try again..."}


@app.get("/user", tags=["Root"])
async def create_user(current_user: dict = Depends(get_current_user)):
    current_user.pop('password')
    return current_user


@app.get("/user/all", tags=["Root"])
async def create_user(response: Response, current_user: dict = Depends(get_current_user)):
    if current_user.get('user_role') != UserRole.admin.value:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {"Admin only API"}
    users = await database.get_user()
    return users


@app.put("/user/medical-shop/profile", tags=["Root"])
async def medical_shop_profile_update(responses: Response, medical_shop: MedicalShop,
                                      current_user: dict = Depends(get_current_user)):
    """
    :param current_user:
    :type medical_shop: object
    :param medical_shop:
    :type responses: object
    """
    if current_user["user_role"] != UserRole.medical_shop.value:
        responses.status_code = status.HTTP_400_BAD_REQUEST
        return {"Invalid user role passed for profile update"}
    update = database.update_user(username=current_user.get("username"), user_data=medical_shop.dict())
    if not update:
        responses.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"Unable to update medical shop profile please try again..."}


@app.put("/user/doctor/profile", tags=["Root"])
async def doctor_profile_update(responses: Response, doctor: Doctor,
                                current_user: dict = Depends(get_current_user)):
    """
    :param current_user:
    :type doctor: object
    :param doctor:
    :type responses: object
    """
    if current_user["user_role"] != UserRole.doctor.value:
        responses.status_code = status.HTTP_400_BAD_REQUEST
        return {"Invalid user role passed for profile update"}
    update = await database.update_user(username=current_user.get("username"), user_data=doctor.dict())
    if not update:
        responses.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"Unable to update doctor profile please try again..."}
    return {"Successfully updated doctor profile"}


@app.post("/token", response_model=Token, tags=["Root"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.get("username")}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "username": user["username"],
            "role": user.get("user_role")}


@app.get("/patient/{patient_id}", tags=["Root"])
async def get_patients(patient_id, current_user: dict = Depends(get_current_user)):
    # return {"message": "Return patients"}
    patients = await database.get_patient(patient_id=patient_id)
    # print(patients)
    if patients:
        return patients
    else:
        return {"message": "No patients found in the database"}


@app.get("/patient", tags=["Root"])
async def get_patients(response: Response, mobile_no: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    patients = await database.get_patient(mobile_no=mobile_no)
    if patients:
        return patients
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        return []


@app.post("/patient", tags=["Root"], )
async def add_patients(patient: Patient, current_user: dict = Depends(get_current_user)):
    new_patient = await database.add_patient(patient.dict())
    return {"patient_id": str(new_patient.inserted_id), "message": "Successfully added patient"}


@app.get("/doctor/external", tags=["Root"])
async def get_external_doctor(current_user: dict = Depends(get_current_user), mobile_no: Optional[int] = None,
                              specialisation: Optional[str] = None,
                              doctor_id: Optional[str] = None):
    doctors = await database.get_external_doctor(mobile_no=mobile_no, specialisation=specialisation,
                                                 doctor_id=doctor_id)
    if doctors:
        return doctors
    else:
        return {"message": "No doctors found in the database"}


@app.post("/doctor/external", tags=["Root"], )
async def add_doctor(doctor: ExternalDoctor, current_user: dict = Depends(get_current_user)):
    new_doctor = await database.add_doctor(doctor.dict())
    return {"doctor_id": str(new_doctor.inserted_id), "message": "Successfully added doctor"}


@app.get("/patient/{patient_id}/appointment/{appointment_id}", tags=["Root"])
async def get_appointments(patient_id, appointment_id, current_user: dict = Depends(get_current_user)):
    # return {"message": "Return patients"}
    appointment = await database.get_appointment(patient_id=patient_id, appointment_id=appointment_id)
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}


@app.get("/patient/{patient_id}/appointment", tags=["Root"])
async def get_appointments(patient_id, current_user: dict = Depends(get_current_user)):
    # return {"message": "Return patients"}
    appointment = await database.get_appointment(patient_id=patient_id)
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}


@app.post("/patient/{patient_id}/appointment", tags=["Root"])
async def create_appointment(patient_id, appointment: Appointment, current_user: dict = Depends(get_current_user)):
    new_appointment = await database.create_appointment(patient_id=patient_id, in_app=appointment.dict())
    if new_appointment is not None:
        # print(new_appointment)
        medical_shop_user = await database.get_user(username=appointment.medical_shop_id)
        try:
            await manager.send_json({"appointment_updated": True}, medical_shop_user["assigned_doctor"])
        except WebSocketDisconnect:
            manager.disconnect(medical_shop_user)
        return {"appointment_id": str(new_appointment.inserted_id), "message": "Successfully added patient"}
    else:
        return {"message": "Parent ID: {} not found in database".format(patient_id)}


@app.put("/patient/{patient_id}/appointment/{appointment_id}", tags=["Root"])
async def update_appointment_vital(patient_id, appointment_id, vital: Vital,
                                   current_user: dict = Depends(get_current_user)):
    updated = await database.update_appointment_vital(vital=vital.dict(), patient_id=patient_id,
                                                      appointment_id=appointment_id)
    if updated:
        return {"_id": appointment_id, "message": "Successfully updated vital"}
    else:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}


@app.put("/patient/{patient_id}/appointment/{appointment_id}/prescription", tags=["Root"])
async def add_prescription(patient_id, appointment_id, prescription: Prescription,
                           current_user: dict = Depends(get_current_user)):
    new_prescription = await database.add_appointment_prescription(prescription=prescription.dict(),
                                                                   patient_id=patient_id, appointment_id=appointment_id)
    if new_prescription:
        return {"_id": appointment_id, "message": "Successfully updated prescription"}
    else:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}


@app.get("/patient/{patient_id}/appointment/{appointment_id}/prescription", tags=["Root"])
async def get_prescription(patient_id, appointment_id, current_user: dict = Depends(get_current_user)):
    appointment = await database.get_appointment(patient_id=patient_id, appointment_id=appointment_id)
    if appointment is None:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}
    elif appointment.get("prescription"):
        return appointment.get("prescription")
    else:
        return {"message": "No prescription found in the database"}


@app.put("/patient/{patient_id}/appointment/{appointment_id}/referral", tags=["Root"])
async def add_referral(patient_id, appointment_id, referral: ReferralDoctor,
                       current_user: dict = Depends(get_current_user)):
    new_referral = await database.add_appointment_referral(referral_doctor=referral.dict(), patient_id=patient_id,
                                                           appointment_id=appointment_id)
    if new_referral:
        return {"_id": appointment_id, "message": "Successfully updated referral"}
    else:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}


@app.get("/patient/{patient_id}/appointment/{appointment_id}/referral", tags=["Root"])
async def get_referral(patient_id, appointment_id, current_user: dict = Depends(get_current_user)):
    appointment = await database.get_appointment(patient_id=patient_id, appointment_id=appointment_id)
    if appointment is None:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}
    elif appointment.get("referral"):
        doctor = await database.get_external_doctor(doctor_id=appointment.get("referral"))
        return doctor
    else:
        return {"message": "No referral found in the database"}


@app.put("/patient/{patient_id}/appointment/{appointment_id}/status", tags=["Root"])
async def update_status(patient_id, appointment_id, appointment_status: AppointmentStatus,
                        current_user: dict = Depends(get_current_user)):
    new_status = await database.update_appointment_status(patient_id=patient_id, appointment_id=appointment_id,
                                                          status=appointment_status)
    if new_status:
        if appointment_status is AppointmentStatus.VIDEO_CALL:
            appointment = await database.get_appointment(patient_id=patient_id, appointment_id=appointment_id)
            medical_shop_id = appointment["medical_shop_id"]
            try:
                await manager.send_json({"patient_name": appointment["patient"]["name"],
                                         "patient_id": patient_id, "appointment_id": appointment_id,
                                         "status": AppointmentStatus.VIDEO_CALL.value},
                                        medical_shop_id)
            except WebSocketDisconnect:
                manager.disconnect(medical_shop_id)
        if appointment_status is AppointmentStatus.COMPLETED:
            appointment = await database.get_appointment(patient_id=patient_id, appointment_id=appointment_id)
            medical_shop_id = appointment["medical_shop_id"]
            try:
                await manager.send_json({"patient_name": appointment["patient"]["name"],
                                         "patient_id": patient_id, "appointment_id": appointment_id,
                                         "status": AppointmentStatus.COMPLETED.value},
                                        medical_shop_id)
            except WebSocketDisconnect:
                manager.disconnect(medical_shop_id)

        return {"_id": appointment_id, "message": "Successfully updated appointment status"}
    else:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}


@app.get("/patient/{patient_id}/appointment/{appointment_id}/status", tags=["Root"])
async def get_status(patient_id, appointment_id, current_user: dict = Depends(get_current_user)):
    appointment = await database.get_appointment(patient_id=patient_id, appointment_id=appointment_id)
    if appointment is None:
        return {"message": "No appointment found with ID: {} in the database".format(appointment_id)}
    elif appointment.get("status"):
        return {"appointment_id": appointment_id, "status": appointment.get("status")}
    else:
        return {"message": "No status found in the database"}


@app.get("/active/appointment", tags=["Root"])
async def get_appointments(current_user: dict = Depends(get_current_user)):
    appointment = await database.active_appointment()
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}


@app.get("/inactive/appointment", tags=["Root"])
async def get_appointments(current_user: dict = Depends(get_current_user)):
    appointment = await database.inactive_appointment()
    appointment.reverse()
    if appointment:
        return appointment
    else:
        return {"message": "No appointment found in the database"}


@app.get("/medicine", tags=["Root"])
async def get_medicine(current_user: dict = Depends(get_current_user), medicine_name: Optional[str] = None,
                       medicine_id: Optional[str] = None):
    medicines = await database.get_medicine(medicine_name=medicine_name, medicine_id=medicine_id)
    if medicines:
        return medicines
    else:
        return {"message": "No medicine found in the database"}


@app.post("/medicine", tags=["Root"])
async def get_medicine(medicine: Medicine, current_user: dict = Depends(get_current_user)):
    medicines = await database.add_medicine(medicine.dict())
    if medicines:
        return {"Added medicine with id: {}".format(medicines.inserted_id)}
    else:
        return {"message": "Medicine add failed"}


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    while True:
        data = await websocket.receive_text()


@app.get("/medical-test", tags=["Root"])
async def get_medical_test(current_user: dict = Depends(get_current_user), test_name: Optional[str] = None):
    tests = await database.get_medical_test(test_name=test_name)
    if tests:
        return tests
    else:
        return {"message": "No Medical tests found in the database"}


@app.post("/medical-test", tags=["Root"])
async def add_medical_test(test: Test, current_user: dict = Depends(get_current_user)):
    new_test = await database.add_medical_test(test.dict())
    return {"doctor_id": str(new_test.inserted_id), "message": "Successfully added test"}


@app.get("/pre-existing-disease", tags=["Root"])
async def get_pre_existing_disease(current_user: dict = Depends(get_current_user), disease_name: Optional[str] = None):
    diseases = await database.get_pre_existing_disease(disease_name=disease_name)
    if diseases:
        return diseases
    else:
        return {"message": "No diseases found in the database"}


@app.post("/pre-existing-disease", tags=["Root"])
async def add_pre_existing_disease(disease: PreExistingDisease, current_user: dict = Depends(get_current_user)):
    new_disease = await database.add_pre_existing_disease(disease.dict())
    return {"doctor_id": str(new_disease.inserted_id), "message": "Successfully added Pre existing disease"}

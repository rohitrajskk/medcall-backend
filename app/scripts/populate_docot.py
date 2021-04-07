import json
import requests

url = "http://localhost:8000/doctor/external"
headers = {
    'Content-Type': 'application/json'
}
with open("../data/doctor.json", 'r') as fp:
    doctors = json.load(fp)

responses = []
for doctor in doctors:
    response = requests.request("POST", url, headers=headers, data=json.dumps(doctor))
    responses.append(response)

print(responses)
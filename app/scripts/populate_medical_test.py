import json
import requests

url = "http://localhost:8000/medical-test"
headers = {
    'Content-Type': 'application/json'
}
with open("../data/medical_test.json", 'r') as fp:
    tests = json.load(fp)

responses = []
for test in tests:
    response = requests.request("POST", url, headers=headers, data=json.dumps(test))
    responses.append(response)

print(responses)

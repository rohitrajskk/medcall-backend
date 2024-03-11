import jwt
import datetime
import json
import requests

api_key = ''
api_sec = ''

def generateToken():
    # generate JWT
    payload = {
        'iss': api_key,
        'exp': datetime.datetime.now() + datetime.timedelta(hours=12)
    }
    return jwt.encode(payload, api_sec)
#TODO: Make a new user on zoom and change credentials
url = "https://api.zoom.us/v2/users/vVrN2VbXTuKYYmHqkW0BuA/meetings"
def getmeetings(doc_id: str=None, patient_id: str=None):
    headers = {
        'authorization': 'Bearer {}'.format(generateToken()),
        'content-type': 'application/json'
    }
    body = {
        "topic": "medcall consultation",
        "type": 1,
        "password": "1234",
        "tracking_fields": [
            {
                "field": "patient_id",
                "value": patient_id
            }
        ],
        "settings": {
            "host_video": True,
            "participant_video": True,
            "join_before_host": False,
            "approval_type": 0
        }
    }
    body = json.dumps(body)
    response = requests.post(url, headers=headers, data=body)
    print(response)
    return response.json()


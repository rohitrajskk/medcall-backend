import jwt
import datetime
import json
import requests

token_brearer = ''

# TODO: Make a new user on zoom and change credentials
url = 'https://api.daily.co/v1/rooms'


def getmeetings(doc_id: str = None, patient_id: str = None):
    headers = {
        'authorization': 'Bearer {}'.format(token_brearer),
        'content-type': 'application/json'
    }
    """
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
    """
    response = requests.post(url, headers=headers)
    print(response)
    return response.json()

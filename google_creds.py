
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import os,json

TMP_CREDS_SAVE_PATH = "secrets/gmail_token.json"


SCOPES = [
    # calendar and tasks
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
    # gmail readonly
    "https://www.googleapis.com/auth/gmail.readonly"
]

def clear_saved_credentials():
    if os.path.exists(TMP_CREDS_SAVE_PATH):
        os.remove(TMP_CREDS_SAVE_PATH)

def get_google_client_creds():
    if not os.path.exists(TMP_CREDS_SAVE_PATH):
        flow = InstalledAppFlow.from_client_secrets_file(
            "secrets/gmail_client_secret.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
        with open(TMP_CREDS_SAVE_PATH, "w") as token:
            token.write(creds.to_json())
    else:
        with open(TMP_CREDS_SAVE_PATH, "r") as token:
            creds = Credentials.from_authorized_user_info(json.load(token), SCOPES)
    return creds

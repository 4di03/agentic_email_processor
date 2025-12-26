from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import os
from email_service import EmailService, Email
from typing import Generator


TMP_CREDS_SAVE_PATH = "secrets/gmail_token.json"


if __name__ == "__main__":

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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

    email_service = EmailService(creds)
    try:
        emails : Generator[Email, None, None] = email_service.get_last_n_emails(n=5)
    except Exception as e:
        print("Error fetching emails:", e, "maybe due to invalid creds, deleting creds")
        os.remove(TMP_CREDS_SAVE_PATH)
        exit(1)


    for email in emails:
        print("Subject:", email.subject)
        print("Message Body:", email.body)
        print("\n"* 4)

        

    
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from dataclasses import  dataclass
from typing import Generator
import os,json
TMP_CREDS_SAVE_PATH = "secrets/gmail_token.json"



@dataclass
class Email:
    subject : str
    body : str

    def __str__(self):
        return f"Subject: {self.subject}\nBody: {self.body}"
    

class EmailService:
    """For reading emails from a personal Gmail account using Gmail API."""

    def __init__(self, creds):
        """token for Gmail API access."""
        self.creds = creds


    def _get_subject(self, msg):
        headers = msg["payload"]["headers"]
        for header in headers:
            if header["name"] == "Subject":
                return header["value"]
        return "No Subject"

    def _get_snippet(self, msg):
        return msg.get("snippet", "No Snippet")


    def _get_body(self, msg):
        if "parts" in msg["payload"]:
            parts = msg["payload"]["parts"]
            for part in parts:
                if part["mimeType"] == "text/plain":
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
        if "body" in msg["payload"] and "data" in msg["payload"]["body"]:
            return base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode("utf-8")
        return "No Body"

    def get_last_n_emails(self, n=5) -> Generator[Email, None, None]:
        # generator for the last n emails
        
        # read last 5 email
        service = build("gmail", "v1", credentials=self.creds)
        results = (
            service.users().messages()
            .list(userId="me", maxResults=n)
            .execute()
        )
        messages = results.get("messages", [])
        for msg in messages:
            msg_detail = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"])
                .execute()
            )
            yield Email(
                subject=self._get_subject(msg_detail),
                body=self._get_body(msg_detail),
            )


    @staticmethod   
    def create_email_service():
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

        return EmailService(creds)
    
    @staticmethod
    def clear_saved_credentials():
        if os.path.exists(TMP_CREDS_SAVE_PATH):
            os.remove(TMP_CREDS_SAVE_PATH)
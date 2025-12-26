from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from dataclasses import  dataclass
from typing import Generator
@dataclass
class Email:
    subject : str
    body : str

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
        if "body" in msg["payload"]:
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



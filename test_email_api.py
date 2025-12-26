from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import os
from email_service import EmailService, Email
from typing import Generator






if __name__ == "__main__":

    email_service = EmailService.__class__reate_email_service()
    try:
        emails : Generator[Email, None, None] = email_service.get_last_n_emails(n=5)
    except Exception as e:
        print("Error fetching emails:", e, "maybe due to invalid creds, deleting creds")
        email_service.clear_saved_credentials()
        exit(1)


    for email in emails:
        print("Subject:", email.subject)
        print("Message Body:", email.body)
        print("\n"* 4)

        

    
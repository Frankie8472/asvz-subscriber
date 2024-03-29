# Copyright by your friendly neighborhood SaunaLord
import base64
import pytz
import os
from django.utils import timezone
from pathlib import Path
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


def send_mail(valid_to, email):
    """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    asvz_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    file_path_token = os.path.join(asvz_dir, 'token.json')
    file_path_cred = os.path.join(asvz_dir, 'credentials.json')

    if os.path.exists(file_path_token):
        creds = Credentials.from_authorized_user_file(file_path_token, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(file_path_cred, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(file_path_token, 'w') as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        valid_to_str = valid_to.strftime('%d.%m.%Y')
        message = MIMEText(f'Dear User,\n\nThis is a friendly reminder :)\nYour sauna subscription for ASVZ Hönggerberg is valid until {valid_to_str}, which is in less than 3 days!\n\nThis email is automatic generated and will harass you only three times. If this is a problem for you, try to find inner peace in the sauna ;)\n\nBest,\nYour friendly neighborhood SaunaLord')
        message['subject'] = f'[ASVZ] Your Sauna Subscription is about to run out!'
        message['to'] = email
        message['from'] = 'me'
        raw_message = base64.urlsafe_b64encode(message.as_string().encode("utf-8"))
        send_message(service, 'me', {'raw': raw_message.decode("utf-8")})
    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}', flush=True)
    return


def send_message(service, sender, message):
    try:
        message = service.users().messages().send(userId=sender, body=message).execute()
        return message
    except Exception as e:
        print('An error occurred: %s' % e, flush=True)
        return None


def main():
    current_time = timezone.datetime.now(tz=pytz.timezone('Europe/Zurich'))
    email = ''

    send_mail(current_time, email)
    return


if __name__ == "__main__":
    main()

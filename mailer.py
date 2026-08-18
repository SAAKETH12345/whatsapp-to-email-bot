"""
================================================================================
GMAIL API AUTHENTICATION & FIRST-TIME SETUP INSTRUCTIONS
================================================================================
To authenticate and use the Gmail API for sending emails, follow these steps:

1. Enable Gmail API:
   - Go to Google Cloud Console (https://console.cloud.google.com/).
   - Create a new project or select an existing project.
   - In the API Library, search for "Gmail API" and click "Enable".

2. Configure OAuth Consent Screen:
   - Navigate to "APIs & Services" > "OAuth consent screen".
   - Select User Type ("External" or "Internal") and complete mandatory app details.
   - Add the required scope: `https://www.googleapis.com/auth/gmail.send`
   - Under "Test users", add your Gmail email address.

3. Download OAuth Credentials:
   - Go to "APIs & Services" > "Credentials".
   - Click "Create Credentials" > "OAuth client ID".
   - Choose "Desktop app" as the application type and name it (e.g. "WhatsApp Bridge").
   - Click "Download JSON" and save the file in your project directory as `credentials.json`.

4. First-Time Authorization:
   - The first time `send_email()` runs, it will launch your default web browser
     asking you to log into Google and approve `gmail.send` permissions.
   - Upon authorization, a `token.json` file will automatically be created in this directory.
   - Future runs will load `token.json` automatically without requiring manual login.
================================================================================
"""

import os
import base64
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Load environment variables from .env
load_dotenv()

# Scope required for sending emails via Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def get_gmail_service(allow_interactive: bool = False):
    """
    Authenticates and returns an authorized Gmail API service client instance.
    Handles token loading, refresh, and initial OAuth2 local server flow.
    """
    creds = None
    token_file = os.getenv('GMAIL_TOKEN_FILE', 'token.json')
    credentials_file = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')

    # Load token if existing
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If credentials are not available or invalid, initiate auth process
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(
                    f"OAuth credentials file '{credentials_file}' not found.\n"
                    "Please download credentials.json from Google Cloud Console as described in top header instructions."
                )
            if not allow_interactive:
                raise RuntimeError(
                    "Gmail account is not authenticated yet!\n"
                    "Please run 'python setup_auth.py' in your terminal once to authorize your Gmail account."
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for future executions
        with open(token_file, 'w', encoding='utf-8') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


import urllib.parse

def download_twilio_media(media_url: str, custom_filename: str = None) -> tuple[bytes, str, str]:
    """
    Downloads media file attached to WhatsApp message via Twilio or Green-API Media URL.
    Only passes Twilio basic auth header if the URL is hosted on Twilio.
    Returns (file_bytes, content_type, filename).
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    auth = None
    if account_sid and auth_token and not account_sid.startswith("your_"):
        if "twilio.com" in media_url.lower() or "twiliocdn.com" in media_url.lower():
            auth = (account_sid, auth_token)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"[Media Download] Fetching file from '{media_url}' (Auth: {bool(auth)})...")
    response = requests.get(media_url, auth=auth, headers=headers, timeout=30)
    response.raise_for_status()

    content_type = response.headers.get('Content-Type', 'application/octet-stream')

    filename = custom_filename
    if not filename:
        content_disp = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disp:
            filename = content_disp.split("filename=")[-1].strip('";\'')
        else:
            parsed_path = os.path.basename(urllib.parse.urlparse(media_url).path)
            if parsed_path and '.' in parsed_path and len(parsed_path) > 3 and not parsed_path.startswith("tmp"):
                filename = parsed_path
            else:
                ext = content_type.split('/')[-1] if '/' in content_type else 'bin'
                if ext == 'jpeg': ext = 'jpg'
                filename = f"whatsapp_attachment.{ext}"

    filename = os.path.basename(filename).replace('"', '').replace("'", "")
    print(f"[Media Download] Successfully downloaded {len(response.content)} bytes | MIME: {content_type} | Filename: {filename}")
    return response.content, content_type, filename


def send_email_via_smtp(to_email: str, subject: str, body: str, media_url: str = None, file_name: str = None) -> dict:
    """
    Sends email via Gmail SMTP using standard App Password (bypasses OAuth completely).
    """
    import smtplib
    sender_email = os.getenv("GMAIL_SENDER_EMAIL", "").strip()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")

    if not sender_email or not app_password:
        raise ValueError("Missing GMAIL_SENDER_EMAIL or GMAIL_APP_PASSWORD in .env file.")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # Process and attach media if present
    if media_url:
        try:
            file_data, content_type, filename = download_twilio_media(media_url, custom_filename=file_name)
            maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')

            part = MIMEBase(maintype, subtype)
            part.set_payload(file_data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(part)
        except Exception as err:
            print(f"[SMTP Warning] Failed to download or attach file from {media_url}: {err}")

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)

    return {"status": "sent", "method": "smtp"}


def format_email_mime_parts(body: str) -> MIMEMultipart:
    """
    Cleans literal '\\n' escape sequences, removes leftover bracket placeholders,
    and returns a duly structured MIMEMultipart ('alternative') container with both
    Plain Text and Executive HTML renderings.
    """
    clean_body = body.replace("\\n", "\n").replace("[Recipient Name]", "").replace("[Your Name]", "").replace("[Insert Name]", "").strip()

    alt_msg = MIMEMultipart('alternative')
    alt_msg.attach(MIMEText(clean_body, 'plain', 'utf-8'))

    paragraphs = [p.strip() for p in clean_body.split('\n') if p.strip()]
    html_paragraphs = "".join([f"<p style='margin: 0 0 14px 0; line-height: 1.6; font-size: 15px;'>{p}</p>" for p in paragraphs])
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 15px; color: #1e293b; line-height: 1.6; margin: 0; padding: 20px; }}
    p {{ margin-bottom: 14px; line-height: 1.6; font-size: 15px; }}
  </style>
</head>
<body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 15px; color: #1e293b; line-height: 1.6; padding: 10px;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff;">
    {html_paragraphs}
  </div>
</body>
</html>"""

    alt_msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    return alt_msg


def send_email(to_email: str, subject: str, body: str, media_url: str = None, file_name: str = None) -> dict:
    """
    Constructs a standard MIME multipart email message with text body and optional downloaded attachment,
    and sends it via SMTP (if GMAIL_APP_PASSWORD set) or Gmail API.
    """
    sender_email = os.getenv("GMAIL_SENDER_EMAIL", "").strip()
    app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if sender_email and app_password:
        print(f"Sending email via Gmail SMTP ({sender_email})...")
        return send_email_via_smtp(to_email, subject, body, media_url, file_name)

    print("Sending email via Gmail API OAuth...")
    service = get_gmail_service()

    msg = MIMEMultipart('mixed')
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(format_email_mime_parts(body))

    # Process and attach media if present
    if media_url:
        try:
            file_data, content_type, filename = download_twilio_media(media_url, custom_filename=file_name)
            maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')

            part = MIMEBase(maintype, subtype)
            part.set_payload(file_data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(part)
        except Exception as err:
            print(f"[OAuth Warning] Failed to download or attach file from {media_url}: {err}")

    # Encode message as base64 URL-safe string required by Gmail API
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
    message_body = {'raw': raw_message}

    sent_message = service.users().messages().send(
        userId='me',
        body=message_body
    ).execute()

    return sent_message


def send_email_with_user_creds(user_info: dict, to_email: str, subject: str, body: str, media_url: str = None, file_name: str = None) -> dict:
    """
    Sends email using per-user dynamic credentials retrieved from DB (OAuth or SMTP).
    """
    auth_type = user_info.get("auth_type", "oauth")
    creds_data = user_info.get("creds_data", {})
    active_email = user_info.get("active_email", "")

    if auth_type == "smtp":
        import smtplib
        sender_email = creds_data.get("sender_email", active_email)
        app_password = creds_data.get("app_password", "").replace(" ", "")

        msg = MIMEMultipart('mixed')
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(format_email_mime_parts(body))

        if media_url:
            try:
                file_data, content_type, filename = download_twilio_media(media_url, custom_filename=file_name)
                maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')

                part = MIMEBase(maintype, subtype)
                part.set_payload(file_data)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(part)
            except Exception as err:
                print(f"[User SMTP Warning] Failed to attach media: {err}")

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)

        return {"status": "sent", "method": "user_smtp", "sender": sender_email}

    elif auth_type == "oauth":
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build('gmail', 'v1', credentials=creds)

        msg = MIMEMultipart('mixed')
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(format_email_mime_parts(body))

        if media_url:
            try:
                file_data, content_type, filename = download_twilio_media(media_url, custom_filename=file_name)
                maintype, subtype = content_type.split('/', 1) if '/' in content_type else ('application', 'octet-stream')

                part = MIMEBase(maintype, subtype)
                part.set_payload(file_data)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(part)
            except Exception as err:
                print(f"[User OAuth Warning] Failed to attach media: {err}")

        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        message_body = {'raw': raw_message}

        sent_message = service.users().messages().send(userId='me', body=message_body).execute()
        return sent_message

    raise ValueError(f"Unknown auth_type: {auth_type}")


if __name__ == "__main__":
    print("Mailer module loaded. Call send_email(to_email, subject, body, media_url) to send emails.")

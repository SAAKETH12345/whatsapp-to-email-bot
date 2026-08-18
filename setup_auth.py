import os
import sys
import webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    token_file = os.getenv('GMAIL_TOKEN_FILE', 'token.json')
    credentials_file = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')

    if not os.path.exists(credentials_file):
        print(f"ERROR: {credentials_file} not found!")
        return

    print("==================================================")
    print("   Gmail OAuth 2.0 One-Time Authentication Setup   ")
    print("==================================================")
    
    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
    
    print("\nStarting local authentication server on http://localhost:8080/ ...")
    print("Opening web browser for Google account login...\n")
    
    creds = flow.run_local_server(port=8080, open_browser=True)

    with open(token_file, 'w', encoding='utf-8') as token:
        token.write(creds.to_json())

    print("\nSUCCESS! Gmail API successfully authenticated.")
    print(f"token.json saved to {token_file}")
    print("The WhatsApp-to-Email bot is now fully authorized to send emails!")

if __name__ == "__main__":
    main()

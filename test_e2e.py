import sys
import json
import requests

BASE_URL = "http://127.0.0.1:5000"
TEST_EMAIL = "testwamailbot@gmail.com"
FAKE_APP_PASSWORD = "Whatsapp@mailbot"

def test_1_smtp_error_handling():
    print("\n--- Test 1: SMTP Authentication Error Handling ---")
    url = f"{BASE_URL}/api/verify-app-password"
    payload = {
        "email": TEST_EMAIL,
        "sender_email": TEST_EMAIL,
        "app_password": FAKE_APP_PASSWORD,
        "is_new_user": True
    }
    
    print(f"Sending POST to {url} with email='{TEST_EMAIL}' and fake password...")
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    assert response.status_code == 401, f"Expected 401 Unauthorized, but got {response.status_code}"
    
    res_json = response.json()
    assert res_json.get("success") is False, f"Expected success: False, but got {res_json}"
    assert "error" in res_json, "Expected 'error' field in JSON response"
    print("SUCCESS: Test 1 Passed! Server safely caught SMTP rejection and returned 401 Unauthorized JSON response.")

def test_2_and_3_greenapi_webhook_ai_pipeline():
    print("\n--- Test 2 & 3: Green API Webhook & AI Pipeline ---")
    url = f"{BASE_URL}/mailbot"
    
    payload = {
        "typeWebhook": "incomingMessageReceived",
        "instanceData": {
            "idInstance": 12345678,
            "wid": "12345678@c.us",
            "typeInstance": "whatsapp"
        },
        "timestamp": 1690000000,
        "idMessage": "3EB0123456789",
        "senderData": {
            "chatId": "919059130576@c.us",
            "sender": "919059130576@c.us",
            "senderName": "Staging User"
        },
        "messageData": {
            "typeMessage": "textMessage",
            "textMessageData": {
                "textMessage": f"Draft an email to {TEST_EMAIL} to verify the AI pipeline is fully operational."
            }
        }
    }
    
    print(f"Sending Green API Webhook POST to {url}...")
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    assert response.status_code == 200, f"Expected 200 OK, but got {response.status_code}"
    
    body_str = response.text
    assert "Email Draft Ready" in body_str or "success" in body_str or TEST_EMAIL in body_str, \
        f"Expected response to contain draft success message, got: {body_str}"
    assert "Sending From:" in body_str or "Sending From" in body_str, \
        f"Expected response to include Sending From email string, got: {body_str}"
    
    print("SUCCESS: Test 2 & 3 Passed! Green API Webhook & AI Pipeline returned 200 OK with success draft message and Sending From email.")

def test_4_current_user_and_logout():
    print("\n--- Test 4: Current User API & Logout Session Handling ---")
    session_req = requests.Session()
    
    # 1. Verify unauthenticated status
    res = session_req.get(f"{BASE_URL}/api/current-user")
    print(f"Current User API: Status {res.status_code} | Body {res.text}")
    assert res.status_code == 200
    assert "logged_in" in res.json()
    
    # 2. Verify /logout endpoint returns redirect
    logout_res = session_req.get(f"{BASE_URL}/logout", allow_redirects=False)
    print(f"Logout Response Code: {logout_res.status_code}")
    assert logout_res.status_code in (302, 303, 200)
    print("SUCCESS: Test 4 Passed! /api/current-user and /logout endpoints are functioning cleanly.")

if __name__ == "__main__":
    print("Starting End-to-End Automated Diagnostic Suite...")
    try:
        test_1_smtp_error_handling()
        test_2_and_3_greenapi_webhook_ai_pipeline()
        test_4_current_user_and_logout()
        print("\nALL E2E DIAGNOSTIC TESTS PASSED CLEANLY!")
        sys.exit(0)
    except AssertionError as ae:
        print(f"\nTEST FAILURE: {ae}")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\nUNHANDLED EXCEPTION: {e}")
        traceback.print_exc()
        sys.exit(1)

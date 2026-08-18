import os
import re
import json
import smtplib
import requests
import urllib.parse
from flask import Flask, request, Response, render_template_string, redirect, url_for, send_from_directory, jsonify, session
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

from ai_agent import draft_email
from mailer import send_email, send_email_with_user_creds
import db

import time

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "whatsapp-mailbot-ai-secure-session-key-998877665544332211")

@app.route("/", methods=["GET", "HEAD"])
@app.route("/health", methods=["GET", "HEAD"])
def index_health_check():
    return Response("WhatsApp AI Mail Bot is Live & Ready!", status=200, mimetype="text/plain")

@app.route("/qr")
def qr_scanner_page():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WhatsApp 24/7 Cloud QR Scanner</title>
        <meta http-equiv="refresh" content="5">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: system-ui, -apple-system, sans-serif; background: #0b141a; color: #e9edef; text-align: center; padding: 2rem 1rem; margin: 0; }
            .card { background: #111b21; border-radius: 16px; padding: 2rem; max-width: 440px; margin: 0 auto; box-shadow: 0 12px 32px rgba(0,0,0,0.6); border: 1px solid #222d34; }
            h2 { color: #00a884; margin-top: 0; }
            .badge { background: #00a884; color: #111b21; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; display: inline-block; margin-bottom: 1rem; }
            img { width: 100%; max-width: 320px; height: auto; border-radius: 12px; border: 4px solid #00a884; background: #fff; }
            p { color: #8696a0; font-size: 0.95rem; line-height: 1.5; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>⚡ WhatsApp Cloud Bot QR</h2>
            <div><span class="badge">🔄 Auto-Refreshing Live QR Code</span></div>
            <p>Open WhatsApp → <b>Linked Devices</b> → Scan QR Code below:</p>
            <img src="/static/qr.png?t={{ timestamp }}" alt="Fresh WhatsApp QR Code">
            <p style="margin-top: 1.5rem;">Number: <b>+91 63059 70096</b></p>
        </div>
    </body>
    </html>
    """, timestamp=int(time.time()))

# Base public URL (dynamic ngrok or host)
def get_base_url():
    try:
        import urllib.request
        res = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=1)
        data = json.loads(res.read().decode())
        return data["tunnels"][0]["public_url"]
    except Exception:
        return f"http://localhost:{os.getenv('FLASK_PORT', 5000)}"


def send_twilio_whatsapp_message(to_phone: str, message_body: str):
    """
    Sends an async WhatsApp notification message via Twilio REST API.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
    
    if account_sid and auth_token and not account_sid.startswith("your_"):
        try:
            client = Client(account_sid, auth_token)
            client.messages.create(
                from_=from_number,
                to=to_phone,
                body=message_body
            )
        except Exception as err:
            print(f"Twilio REST notification error: {err}")


def send_whatsapp_notification(to_phone: str, message_body: str):
    """
    Sends an outbound WhatsApp notification to specified phone number via Green API and/or Twilio.
    """
    if not to_phone:
        return

    clean_phone = to_phone.strip().replace("whatsapp:", "").replace(" ", "")
    chat_id = clean_phone.replace("+", "") + "@c.us"

    try:
        send_green_api_message(chat_id, message_body)
    except Exception as err:
        print(f"Green API Notification Error: {err}")

    try:
        send_twilio_whatsapp_message(to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}", message_body)
    except Exception as err:
        print(f"Twilio Notification Error: {err}")


def extract_recipient_and_brief(raw_body: str) -> tuple[str, str]:
    default_email = os.getenv("DEFAULT_RECIPIENT_EMAIL", "").strip()
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    match = re.search(email_pattern, raw_body)
    
    if match:
        target_email = match.group(0)
        brief = raw_body.replace(target_email, "")
        brief = re.sub(r'^(?:draft\s+(?:an?\s+)?email\s+(?:to\s+)?|send\s+(?:an?\s+)?email\s+(?:to\s+)?|to:?)\s*', '', brief, flags=re.IGNORECASE).strip()
        if brief.startswith("|") or brief.startswith("-"):
            brief = brief[1:].strip()
        return target_email, brief if brief else raw_body
    
    return default_email, raw_body


# HTML Template for Web Authentication Portal - OKC Media Editorial Technical Dossier Edition
AUTH_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Mail Bot AI — Sign In & Connect Gmail</title>
    
    <!-- Open Graph & WhatsApp Link Preview Meta Tags -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="WhatsApp Mail Bot AI — Sign In & Connect Gmail">
    <meta property="og:description" content="Authorize your Gmail account to automate email drafting, review, and dispatch directly inside WhatsApp.">
    <meta property="og:image" content="{{ request.host_url.rstrip('/') }}/static/uploads/cap_0_gemini_ai_brief.png">
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:title" content="WhatsApp Mail Bot AI — Sign In & Connect Gmail">
    <meta property="twitter:description" content="Authorize your Gmail account to automate email drafting, review, and dispatch directly inside WhatsApp.">
    <meta property="twitter:image" content="{{ request.host_url.rstrip('/') }}/static/uploads/cap_0_gemini_ai_brief.png">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Lenis Smooth Scroll CSS -->
    <link rel="stylesheet" href="https://unpkg.com/lenis@1.1.9/dist/lenis.css">

    <!-- GSAP, ScrollTrigger & Studio Freight Lenis Smooth Scroll CDNs -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
    <script src="https://unpkg.com/@studio-freight/lenis@1.0.34/dist/lenis.min.js"></script>

    <style>
        :root {
            --bg-dark: #0a0a0a;
            --card-bg: rgba(255, 255, 255, 0.02);
            --text-heading: #ffffff;
            --text-body: rgba(255, 255, 255, 0.6);
            --text-muted: rgba(255, 255, 255, 0.4);
            --border-subtle: rgba(255, 255, 255, 0.06);
            --accent-light-blue: #60a5fa;
            --accent-green: #25D366;
            --navbar-bg: rgba(10, 10, 10, 0.85);
            --modal-bg: #000000;
            --input-bg: rgba(0, 0, 0, 0.5);
            --ease-expo: cubic-bezier(0.16, 1, 0.3, 1);
        }

        /* Light Theme Auto/Manual Overrides */
        [data-theme="light"] {
            --bg-dark: #f8fafc;
            --card-bg: rgba(0, 0, 0, 0.02);
            --text-heading: #0f172a;
            --text-body: rgba(15, 23, 42, 0.7);
            --text-muted: rgba(15, 23, 42, 0.5);
            --border-subtle: rgba(0, 0, 0, 0.08);
            --accent-light-blue: #2563eb;
            --navbar-bg: rgba(248, 250, 252, 0.85);
            --modal-bg: #ffffff;
            --input-bg: rgba(255, 255, 255, 0.9);
        }

        * { 
            box-sizing: border-box; 
            margin: 0; 
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        html, body {
            background-color: var(--bg-dark);
            color: var(--text-heading);
            width: 100%;
            min-height: 100vh;
            overflow-x: hidden;
            transition: background-color 0.4s var(--ease-expo), color 0.4s var(--ease-expo);
        }

        /* All Headings & Body Typography Strictly Sans-Serif */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
            letter-spacing: -0.04em;
            font-weight: 400;
            color: var(--text-heading);
        }

        p, span, label, div {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-weight: 300;
            color: var(--text-body);
            line-height: 1.5;
        }

        .mono-tag {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 500;
        }

        /* GPU Hardware Acceleration Fixes */
        .will-gpu {
            will-change: transform, opacity;
            transform: translate3d(0, 0, 0);
        }

        /* Lenis Smooth Scroll Fixes */
        html.lenis, html.lenis body { height: auto; }
        .lenis.lenis-smooth { scroll-behavior: auto !important; }

        /* Ambient Glowing Aura Canvas & Antigravity Orbs */
        #physics-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 0;
            pointer-events: none;
            opacity: 0.85;
            transition: opacity 0.5s ease;
        }

        .antigravity-aura-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 0;
            pointer-events: none;
            overflow: hidden;
        }

        .antigravity-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(100px);
            opacity: 0.45;
            will-change: transform;
            transition: background 0.6s var(--ease-expo);
        }

        .antigravity-orb-1 {
            width: 600px;
            height: 600px;
            top: -150px;
            left: -150px;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.4) 0%, rgba(6, 182, 212, 0.15) 70%, transparent 100%);
            animation: orbFloat1 18s ease-in-out infinite alternate;
        }

        .antigravity-orb-2 {
            width: 700px;
            height: 700px;
            bottom: -200px;
            right: -150px;
            background: radial-gradient(circle, rgba(168, 85, 247, 0.35) 0%, rgba(37, 211, 102, 0.12) 70%, transparent 100%);
            animation: orbFloat2 22s ease-in-out infinite alternate;
        }

        .antigravity-orb-3 {
            width: 500px;
            height: 500px;
            top: 40%;
            left: 30%;
            background: radial-gradient(circle, rgba(6, 182, 212, 0.25) 0%, rgba(99, 102, 241, 0.1) 70%, transparent 100%);
            animation: orbFloat3 14s ease-in-out infinite alternate;
        }

        [data-theme="light"] .antigravity-orb-1 {
            background: radial-gradient(circle, rgba(37, 99, 235, 0.35) 0%, rgba(79, 70, 229, 0.15) 70%, transparent 100%);
            opacity: 0.6;
        }

        [data-theme="light"] .antigravity-orb-2 {
            background: radial-gradient(circle, rgba(124, 58, 237, 0.3) 0%, rgba(13, 148, 136, 0.15) 70%, transparent 100%);
            opacity: 0.6;
        }

        [data-theme="light"] .antigravity-orb-3 {
            background: radial-gradient(circle, rgba(14, 165, 233, 0.28) 0%, rgba(37, 99, 235, 0.1) 70%, transparent 100%);
            opacity: 0.6;
        }

        @keyframes orbFloat1 {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(120px, 80px) scale(1.15); }
        }

        @keyframes orbFloat2 {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(-100px, -120px) scale(1.2); }
        }

        @keyframes orbFloat3 {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(60px, -90px) scale(0.9); }
        }

        /* Section 1: Global Glassy Fixed Navigation Bar */
        .navbar {
            width: 100%;
            height: 84px;
            padding: 0 5%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: fixed;
            top: 0;
            left: 0;
            z-index: 100;
            background: var(--navbar-bg);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-bottom: 1px solid var(--border-subtle);
            transition: background 0.4s var(--ease-expo);
        }

        .brand-logo {
            display: flex;
            align-items: center;
            gap: 14px;
            text-decoration: none;
            color: var(--text-heading);
            font-weight: 400;
            font-size: 19px;
            letter-spacing: -0.04em;
        }

        .brand-logo-icon {
            width: 34px;
            height: 34px;
            filter: grayscale(0.2) drop-shadow(0 4px 12px rgba(37, 211, 102, 0.2));
        }

        .nav-right-group {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .theme-toggle-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-subtle);
            color: var(--text-heading);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: all 0.4s var(--ease-expo);
        }

        .theme-toggle-btn:hover {
            transform: scale(1.08);
            border-color: var(--accent-light-blue);
        }

        .nav-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(37, 211, 102, 0.05);
            color: #4ade80;
            border: 1px solid rgba(74, 222, 128, 0.15);
            padding: 5px 14px;
            border-radius: 999px;
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .pulse-dot {
            width: 6px;
            height: 6px;
            background: #4ade80;
            border-radius: 50%;
            box-shadow: 0 0 8px #4ade80;
            animation: pulseDot 2s infinite var(--ease-expo);
        }

        @keyframes pulseDot {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.4); opacity: 0.4; }
        }

        @keyframes avatarGlowPulse {
            0%, 100% {
                box-shadow: 0 0 20px rgba(0, 255, 150, 0.15), 0 0 40px rgba(0, 255, 150, 0.05);
                transform: scale(1);
            }
            50% {
                box-shadow: 0 0 35px rgba(0, 255, 150, 0.3), 0 0 60px rgba(0, 255, 150, 0.1);
                transform: scale(1.02);
            }
        }

        @keyframes radarPulse {
            0% {
                box-shadow: 0 0 0 0 rgba(0, 255, 100, 0.4), 0 0 0 0 rgba(0, 255, 100, 0.2);
            }
            50% {
                box-shadow: 0 0 0 5px rgba(0, 255, 100, 0.2), 0 0 0 10px rgba(0, 255, 100, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(0, 255, 100, 0), 0 0 0 0 rgba(0, 255, 100, 0);
            }
        }

        .radar-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #00ff64;
            display: inline-block;
            flex-shrink: 0;
            animation: radarPulse 2s infinite;
        }

        .shimmer-badge-text {
            background: linear-gradient(120deg, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 1) 50%, rgba(255, 255, 255, 0.4) 100%);
            background-size: 200% auto;
            color: transparent;
            -webkit-background-clip: text;
            background-clip: text;
            animation: textShimmer 3.5s linear infinite;
        }

        @keyframes textShimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        #btn-logout:hover {
            border-color: rgba(255, 68, 68, 0.4) !important;
            color: #ff4444 !important;
            background: rgba(255, 68, 68, 0.06) !important;
        }

        @keyframes statusDotPulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(0, 240, 255, 0.8); transform: scale(1); }
            50% { opacity: 0.35; box-shadow: 0 0 2px rgba(0, 240, 255, 0.3); transform: scale(0.85); }
        }

        .btn-nav-devs {
            background: transparent !important;
            color: var(--text-heading) !important;
            border: 1px solid var(--border-subtle) !important;
            padding: 8px 18px !important;
            border-radius: 999px !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            font-size: 0.75rem !important;
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.1em !important;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            outline: none;
            position: relative;
            user-select: none;
            will-change: transform;
        }

        .dev-status-dot {
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: #00f0ff;
            box-shadow: 0 0 6px rgba(0, 240, 255, 0.8);
            display: inline-block;
            animation: statusDotPulse 2.5s ease-in-out infinite;
            flex-shrink: 0;
        }

        .dev-btn-text {
            display: inline-block;
            letter-spacing: 0.1em;
            transition: letter-spacing 0.3s ease;
        }

        .dev-btn-arrow {
            display: inline-block;
            font-family: inherit;
            font-size: 0.8rem;
            opacity: 0.6;
            transition: transform 0.3s ease, opacity 0.3s ease;
        }

        /* Functional App Passwords Direct Link Button */
        .btn-nav-passwords {
            background: rgba(255, 255, 255, 0.04);
            color: var(--text-heading);
            border: 1px solid var(--border-subtle);
            padding: 12px 24px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 400;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            transition: all 0.5s var(--ease-expo);
        }

        .btn-nav-passwords .arrow-icon {
            transition: transform 0.5s var(--ease-expo);
        }

        .btn-nav-passwords:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }

        .btn-nav-passwords:hover .arrow-icon {
            transform: translate(3px, -3px);
        }

        /* Section 2: Monumental Hero Section with 15vh Whitespace */
        .hero-container {
            width: 100%;
            max-width: 1240px;
            margin: 0 auto;
            padding: 16vh 5% 8vh;
            text-align: center;
            position: relative;
            z-index: 10;
        }

        .hero-brand-tag {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 12px;
            font-weight: 500;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            color: var(--accent-light-blue);
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-subtle);
            padding: 8px 22px;
            border-radius: 999px;
            margin-bottom: 32px;
        }

        .hero-title {
            font-size: clamp(3rem, 6.8vw, 5.8rem);
            font-weight: 300;
            line-height: 1.06;
            letter-spacing: -0.04em;
            color: var(--text-heading);
            margin-bottom: 28px;
        }

        .hero-subtitle {
            font-size: 18px;
            color: var(--text-body);
            max-width: 720px;
            margin: 0 auto 52px;
            line-height: 1.6;
            font-weight: 300;
        }

        /* Stealth Luxury Tab Switcher */
        .switcher-container {
            display: inline-flex;
            background: rgba(0, 0, 0, 0.06);
            border: 1px solid var(--border-subtle);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            padding: 4px;
            border-radius: 999px;
            position: relative;
            margin-bottom: 60px;
            width: 100%;
            max-width: 680px;
        }

        .switcher-pill {
            position: absolute;
            top: 4px;
            left: 0;
            height: calc(100% - 8px);
            width: 33.333%;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border-subtle);
            backdrop-filter: blur(10px);
            border-radius: 999px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            z-index: 1;
            pointer-events: none;
            will-change: transform, width;
        }

        .switcher-btn {
            position: relative;
            z-index: 2;
            padding: 15px 24px;
            border-radius: 999px;
            border: none;
            background: transparent;
            font-size: 14px;
            font-weight: 400;
            cursor: pointer;
            transition: color 0.4s var(--ease-expo);
            display: inline-flex;
            align-items: center;
            gap: 8px;
            flex: 1;
            justify-content: center;
        }

        .switcher-btn.active { color: var(--text-heading); }
        .switcher-btn:not(.active) { color: var(--text-muted); }
        .switcher-btn:not(.active):hover { color: var(--text-heading); }

        /* Integrated Panel Containers */
        .auth-card-box {
            width: 100%;
            max-width: 960px;
            margin: 0 auto;
            background: var(--card-bg);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            border-radius: 32px;
            padding: 56px 48px;
            border: 1px solid var(--border-subtle);
            box-shadow: 0 40px 100px -20px rgba(0, 0, 0, 0.4);
            text-align: left;
            will-change: transform, opacity;
        }

        .form-panel { display: block; }
        .capabilities-panel { display: none; }
        .guide-panel { display: none; }
        .developers-panel { display: none; }

        /* Directive 3: Drawer CSS Strictly Scoped to Side Modals Only */
        #devs-modal-card,
        .devs-modal-card,
        #modal-card,
        .modal-card {
            height: 100dvh !important;
            max-height: 100vh !important;
            overflow-y: auto !important;
            overscroll-behavior: contain !important;
            -webkit-overflow-scrolling: touch !important;
            padding-bottom: 15vh !important;
            box-sizing: border-box !important;
            will-change: transform, scroll-position;
            scrollbar-width: none !important; /* Firefox */
            -ms-overflow-style: none !important; /* IE/Edge */
        }

        #devs-modal-card::-webkit-scrollbar,
        .devs-modal-card::-webkit-scrollbar,
        #modal-card::-webkit-scrollbar,
        .modal-card::-webkit-scrollbar {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
        }

        /* Directive 1: Restore Natural Document Height & Scrolling for Main Page Panels */
        .auth-card-box,
        .capabilities-panel,
        .guide-panel,
        .developers-panel,
        #capabilities-panel,
        #guide-panel,
        #developers-panel,
        .cap-rows-list,
        .developer-rows-list {
            min-height: auto !important;
            height: auto !important;
            max-height: none !important;
            overflow: visible !important;
            overscroll-behavior: auto !important;
        }

        .form-group {
            margin-bottom: 28px;
        }

        label {
            display: block;
            font-size: 13px;
            font-weight: 400;
            color: var(--text-body);
            margin-bottom: 12px;
            letter-spacing: 0.01em;
        }

        .input-wrapper {
            position: relative;
        }

        input {
            width: 100%;
            padding: 18px 26px;
            border-radius: 999px;
            border: 1px solid var(--border-subtle);
            background: var(--input-bg);
            color: var(--text-heading);
            font-size: 15px;
            font-weight: 300;
            outline: none;
            transition: border-color 0.4s var(--ease-expo), box-shadow 0.4s var(--ease-expo);
        }

        input:focus {
            border-color: var(--accent-light-blue);
            box-shadow: 0 0 0 4px rgba(96, 165, 250, 0.12);
        }

        .password-toggle {
            position: absolute;
            right: 22px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            font-weight: 400;
            padding: 6px;
            transition: color 0.3s ease;
        }

        .password-toggle:hover { color: var(--accent-light-blue); }        .btn-connect {
            width: 100%;
            padding: 18px;
            border-radius: 999px;
            background: var(--text-heading);
            color: var(--bg-dark) !important;
            font-size: 15px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: all 0.6s var(--ease-expo);
            margin-top: 14px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            position: relative;
            overflow: hidden;
        }

        .btn-connect span {
            color: var(--bg-dark) !important;
            font-weight: 600 !important;
        }

        [data-theme="light"] .btn-connect {
            background: #0f172a !important;
            color: #ffffff !important;
        }

        [data-theme="light"] .btn-connect span {
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        .btn-connect:hover {
            transform: translateY(-2px) scale(1.01);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
        }

        .divider-container {
            display: flex;
            align-items: center;
            margin: 28px 0;
            color: var(--text-muted);
            font-size: 12px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        .divider-container::before, .divider-container::after {
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border-subtle);
        }

        .divider-container span {
            padding: 0 16px;
        }

        .btn-google-auth {
            width: 100%;
            padding: 16px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-subtle);
            color: var(--text-heading);
            font-size: 14px;
            font-weight: 400;
            cursor: pointer;
            transition: all 0.5s var(--ease-expo);
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            text-decoration: none;
        }

        .btn-google-auth:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }

        /* Engineering Team & Developers Spotlight Cards */
        .developer-cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
        }

        .developer-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-subtle);
            border-radius: 24px;
            padding: 32px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 20px;
            transition: transform 0.4s var(--ease-expo), border-color 0.4s var(--ease-expo), box-shadow 0.4s var(--ease-expo);
        }

        .developer-card:hover {
            transform: translateY(-4px);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        [data-theme="light"] .developer-card {
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        }

        .dev-header {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .dev-avatar {
            width: 52px;
            height: 52px;
            border-radius: 16px;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            color: #ffffff;
            font-weight: 600;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.3);
            flex-shrink: 0;
        }

        .dev-avatar-alt {
            background: linear-gradient(135deg, #0d9488, #25d366);
            box-shadow: 0 8px 20px rgba(13, 148, 136, 0.3);
        }

        .dev-name {
            font-size: 20px;
            font-weight: 500;
            color: var(--text-heading);
            letter-spacing: -0.03em;
        }

        .dev-role {
            font-size: 13px;
            color: var(--accent-light-blue);
            font-weight: 400;
            margin-top: 2px;
        }

        .dev-bio {
            font-size: 14px;
            color: var(--text-body);
            line-height: 1.6;
            font-weight: 300;
        }

        .btn-linkedin {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: rgba(10, 102, 194, 0.12);
            color: #0a66c2;
            border: 1px solid rgba(10, 102, 194, 0.3);
            padding: 12px 22px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.4s var(--ease-expo);
        }

        .btn-linkedin:hover {
            background: #0a66c2;
            color: #ffffff;
            border-color: #0a66c2;
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(10, 102, 194, 0.4);
        }

        .spinner {
            display: none;
            width: 22px;
            height: 22px;
            border: 3px solid rgba(10,10,10,0.3);
            border-radius: 50%;
            border-top-color: #050505;
            animation: spin 0.8s ease-in-out infinite;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        /* Editorial Row Tiles (Pure Editorial, No Grey Hover Box) */
        .cap-rows-list {
            display: flex;
            flex-direction: column;
            width: 100%;
        }

        .cap-row {
            width: 100%;
            display: grid;
            grid-template-columns: 1.4fr 3fr 0.4fr;
            align-items: center;
            padding: 2.2rem 1rem;
            border-bottom: 1px solid var(--border-subtle);
            cursor: pointer;
            background: transparent !important;
            transition: opacity 0.4s var(--ease-expo);
        }

        .cap-rows-list:hover .cap-row:not(:hover) {
            opacity: 0.3;
        }

        .cap-tag {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 0.75rem;
            font-weight: 500;
            letter-spacing: 0.04em;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .cap-row-content {
            transition: transform 0.5s var(--ease-expo);
            will-change: transform;
        }

        .cap-row:hover .cap-row-content {
            transform: translate3d(10px, 0, 0);
        }

        .cap-row-title {
            font-size: 1.75rem;
            font-weight: 400;
            color: var(--text-heading);
            margin-bottom: 6px;
            letter-spacing: -0.04em;
        }

        .cap-row-desc {
            font-size: 14px;
            font-weight: 300;
            color: var(--text-body);
            line-height: 1.5;
        }

        .cap-row-arrow {
            font-size: 22px;
            color: var(--text-muted);
            justify-self: end;
            transition: transform 0.5s var(--ease-expo), color 0.3s ease;
            will-change: transform;
        }

        .cap-row:hover .cap-row-arrow {
            transform: translate3d(12px, 0, 0);
            color: var(--accent-light-blue);
        }

        /* Section 4: App Password Guide Timeline */
        .guide-step {
            display: flex;
            gap: 22px;
            margin-bottom: 28px;
            align-items: flex-start;
        }

        .step-num {
            width: 44px;
            height: 44px;
            background: rgba(37, 99, 235, 0.12);
            color: var(--accent-light-blue);
            border-radius: 50%;
            font-family: 'Inter', sans-serif;
            font-size: 15px;
            font-weight: 500;
            display: flex;
            justify-content: center;
            align-items: center;
            flex-shrink: 0;
            border: 1px solid rgba(59, 130, 246, 0.25);
        }

        .step-text {
            font-size: 15px;
            font-weight: 300;
            color: var(--text-body);
            line-height: 1.6;
            padding-top: 8px;
        }

        .step-text a { color: var(--accent-light-blue); font-weight: 400; text-decoration: none; }
        .step-text a:hover { text-decoration: underline; }

        /* Pure Void Technical Editorial Dossier Modal Drawer */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            z-index: 200;
            display: none;
            justify-content: flex-end;
            opacity: 0;
        }

        .modal-card {
            background: var(--modal-bg);
            height: 100dvh !important;
            max-height: 100vh !important;
            width: 52vw;
            min-width: 500px;
            max-width: 780px;
            border-left: 1px solid var(--border-subtle);
            padding: 0;
            box-shadow: none;
            overflow-y: auto !important;
            overscroll-behavior: contain !important;
            -webkit-overflow-scrolling: touch !important;
            padding-bottom: 15vh !important;
            box-sizing: border-box !important;
            position: relative;
            transform: translate3d(100%, 0, 0);
            will-change: transform, scroll-position;
            scrollbar-width: none !important;
            -ms-overflow-style: none !important;
            pointer-events: auto !important;
        }

        .modal-card::-webkit-scrollbar {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
        }

        /* Directive 2: Boxless Full-Width Editorial Rows for Developers Panel & Modal Drawer */
        .developer-rows-list {
            display: flex;
            flex-direction: column;
            width: 100%;
        }

        .developer-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 32px 0;
            border-bottom: 1px solid var(--border-subtle);
            text-decoration: none;
            color: var(--text-heading);
            position: relative;
            background: transparent !important;
            box-shadow: none !important;
            border-radius: 0 !important;
            cursor: pointer;
            width: 100%;
            box-sizing: border-box;
        }

        .dev-row-main {
            display: flex;
            flex-direction: column;
            flex: 1;
            transition: transform 0.4s var(--ease-expo);
            will-change: transform;
        }

        .dev-row-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 8px;
        }

        .dev-avatar-badge {
            width: 42px;
            height: 42px;
            border-radius: 50%;
            background: transparent !important;
            border: 1px solid var(--text-muted) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-heading);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .dev-row-name {
            font-size: 2rem;
            font-weight: 400;
            letter-spacing: -0.03em;
            color: var(--text-heading);
            margin: 0;
            line-height: 1.1;
        }

        .dev-row-role {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-top: 4px;
        }

        .dev-row-bio {
            color: var(--text-body);
            line-height: 1.6;
            font-size: 0.95rem;
            margin: 10px 0 0 0;
            font-weight: 300;
        }

        .dev-row-arrow {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 1.4rem;
            color: var(--text-heading);
            opacity: 0;
            transform: translateX(-10px);
            transition: opacity 0.4s ease, transform 0.4s ease;
            margin-left: 20px;
            flex-shrink: 0;
            align-self: center;
        }

        .modal-card-content {
            padding: 5vh 3.5vw 200px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            gap: 1.6rem;
            min-height: 100%;
            width: 100%;
            box-sizing: border-box;
            position: relative;
        }

        .modal-close {
            position: absolute;
            top: 3.5vh;
            right: 3.5vw;
            background: none;
            border: none;
            font-size: 2.2rem;
            font-weight: 200;
            color: var(--text-heading);
            cursor: pointer;
            opacity: 0.8;
            transition: opacity 0.3s ease;
            line-height: 1;
            padding: 0;
            z-index: 10;
        }

        .modal-close:hover {
            opacity: 0.4;
        }

        .modal-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: transparent;
            color: #4ade80;
            border: 1px solid rgba(74, 222, 128, 0.2);
            padding: 5px 16px;
            border-radius: 999px;
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 1.5rem;
            width: fit-content;
        }

        .modal-title {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: clamp(2rem, 3.2vw, 2.8rem);
            font-weight: 400;
            letter-spacing: -0.04em;
            line-height: 1.1;
            color: var(--text-heading);
            margin-bottom: 1rem;
        }

        .modal-desc {
            font-family: 'Inter', sans-serif;
            font-weight: 300;
            color: var(--text-body);
            font-size: 1rem;
            line-height: 1.5;
            max-width: 95%;
            margin-bottom: 1rem;
        }

        /* Complete Uncropped iOS iPhone Frame Component (Light Theme matching User Screenshot) */
        .modal-phone-container {
            width: 100%;
            max-width: 360px;
            margin: 0.5rem auto 1rem;
            flex-shrink: 0;
        }

        .modal-phone-frame-img {
            width: 100%;
            display: flex;
            justify-content: center;
        }

        .modal-phone-frame-img img {
            width: 100%;
            max-width: 360px;
            height: auto;
            border-radius: 42px;
            display: block;
            box-shadow: 0 30px 80px -15px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(255, 255, 255, 0.1);
        }

        .modal-scroll-buffer {
            height: 180px;
            width: 100%;
            flex-shrink: 0;
        }

        .modal-phone-frame {
            width: 100%;
            max-width: 360px;
            height: 600px;
            flex-shrink: 0;
            margin: 0 auto;
            background: #efeae2;
            border-radius: 46px;
            border: 10px solid #1c1c1e;
            box-shadow: 0 30px 80px -15px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif;
            display: flex;
            flex-direction: column;
            text-align: left;
            position: relative;
        }

        .phone-top-bar {
            background: #ffffff;
            padding: 8px 20px 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            font-weight: 600;
            color: #000000;
        }

        .phone-notch {
            width: 76px;
            height: 16px;
            background: #000000;
            border-radius: 12px;
        }

        .wa-chat-header {
            background: #ffffff;
            padding: 8px 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            border-bottom: 1px solid #e5e5ea;
        }

        .wa-back-btn {
            color: #007aff;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 2px;
        }

        .wa-avatar {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: #25D366;
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: bold;
            color: white;
            font-size: 14px;
            flex-shrink: 0;
        }

        .wa-chat-info { flex: 1; }
        .wa-chat-name { font-size: 14px; font-weight: 600; color: #000000; }
        .wa-chat-status { font-size: 11px; color: #8e8e93; }

        .wa-header-icons {
            display: flex;
            align-items: center;
            gap: 14px;
            color: #007aff;
            font-size: 16px;
        }

        .wa-chat-body {
            padding: 12px 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            background-color: #efeae2;
            background-image: radial-gradient(rgba(0,0,0,0.03) 1px, transparent 0);
            background-size: 12px 12px;
            flex: 1;
            overflow-y: auto;
        }

        .wa-date-pill {
            align-self: center;
            background: #ffffff;
            color: #8e8e93;
            font-size: 10px;
            font-weight: 500;
            padding: 3px 12px;
            border-radius: 8px;
            margin: 2px 0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .wa-encrypt-warning {
            background: #ffeead;
            color: #524316;
            font-size: 10px;
            line-height: 1.35;
            padding: 6px 10px;
            border-radius: 8px;
            margin: 2px 4px 6px;
            text-align: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .wa-msg {
            max-width: 88%;
            padding: 8px 12px;
            border-radius: 14px;
            font-size: 12px;
            line-height: 1.45;
            position: relative;
            box-shadow: 0 1px 2px rgba(0,0,0,0.06);
        }

        .wa-msg-out {
            align-self: flex-end;
            background: #d9fdd3;
            color: #111b21;
            border-top-right-radius: 2px;
        }

        .wa-msg-in {
            align-self: flex-start;
            background: #ffffff;
            color: #111b21;
            border-top-left-radius: 2px;
        }

        .wa-pdf-card {
            background: rgba(0, 0, 0, 0.04);
            border-radius: 8px;
            padding: 6px 8px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
            border: 1px solid rgba(0, 0, 0, 0.08);
        }

        .wa-pdf-icon {
            width: 26px;
            height: 32px;
            background: #ea4335;
            color: white;
            border-radius: 4px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 9px;
            font-weight: bold;
        }

        .wa-pdf-name { font-size: 11px; font-weight: 600; color: #111b21; }
        .wa-pdf-meta { font-size: 9px; color: #8696a0; }

        .wa-msg-time {
            font-size: 9px;
            color: #8696a0;
            float: right;
            margin-top: 3px;
            margin-left: 6px;
            display: inline-flex;
            align-items: center;
            gap: 2px;
        }

        .wa-checks { color: #34b7f1; font-weight: bold; }

        .wa-chat-footer {
            background: #ffffff;
            padding: 8px 10px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-top: 1px solid #e5e5ea;
        }

        .wa-plus-btn {
            font-size: 18px;
            color: #007aff;
            font-weight: 300;
            line-height: 1;
        }

        .wa-input-pill {
            flex: 1;
            background: #f2f2f7;
            border: 1px solid #e5e5ea;
            padding: 6px 12px;
            border-radius: 18px;
            font-size: 12px;
            color: #8e8e93;
        }

        .wa-footer-icons {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 15px;
            color: #007aff;
        }

        .phone-bottom-bar {
            background: #ffffff;
            padding: 6px 0 10px;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .phone-home-indicator {
            width: 120px;
            height: 4px;
            background: #000000;
            border-radius: 999px;
        }

        /* Pure Stark Sans-Serif Fact Box */
        .modal-fact-box {
            border-left: 1px solid var(--border-subtle);
            padding-left: 1.5rem;
            border-top: none;
            border-right: none;
            border-bottom: none;
            background: transparent;
        }

        .fact-item {
            margin-bottom: 1.2rem;
        }

        .fact-label {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 0.7rem;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 2px;
            display: block;
        }

        .fact-value {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 0.95rem;
            font-weight: 400;
            color: var(--text-heading);
            line-height: 1.4;
        }

        .fact-action-pulse {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 0.7rem;
            font-weight: 500;
            color: #4ade80;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 0.5rem;
        }

        /* Technical Workflow & Practical Explanation Box */
        .modal-explanation-box {
            border-top: 1px solid var(--border-subtle);
            padding-top: 1.8rem;
            margin-top: 0.5rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .explanation-header {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--accent-light-blue);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.2rem;
        }

        .explanation-card {
            background: var(--card-bg);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 1.2rem 1.4rem;
            display: flex;
            gap: 1rem;
            align-items: flex-start;
        }

        .explanation-num {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: rgba(37, 211, 102, 0.1);
            color: #4ade80;
            border: 1px solid rgba(74, 222, 128, 0.2);
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 12px;
            font-weight: 600;
            flex-shrink: 0;
        }

        .explanation-content-title {
            font-size: 0.95rem;
            font-weight: 500;
            color: var(--text-heading);
            margin-bottom: 4px;
        }

        .explanation-content-text {
            font-size: 0.85rem;
            font-weight: 300;
            color: var(--text-body);
            line-height: 1.5;
        }

        .brand-title-full { display: inline; }
        .brand-title-short { display: none; }

        .auth-card-box {
            max-width: 100%;
            overflow: hidden;
            box-sizing: border-box;
            word-break: break-word;
            overflow-wrap: anywhere;
        }

        .step-text {
            word-break: break-word;
            overflow-wrap: anywhere;
        }

        .step-text a {
            word-break: break-all;
        }

        /* Full Mobile UI Ergonomics & High Refresh Touch Support */
        @media (max-width: 768px) {
            .navbar { padding: 0 0.8rem; height: 64px; max-width: 100vw; box-sizing: border-box; overflow: hidden; }
            .brand-logo { font-size: 14px; gap: 6px; }
            .brand-logo svg { width: 28px; height: 28px; flex-shrink: 0; }
            .nav-right-group { gap: 4px; flex-shrink: 0; }
            .btn-nav-devs { padding: 6px 10px; font-size: 11px; height: 36px; min-height: 36px; }
            .btn-nav-passwords { padding: 6px 10px; font-size: 11px; height: 36px; min-height: 36px; }
            .theme-toggle-btn { width: 34px; height: 34px; min-height: 34px; flex-shrink: 0; }
            
            .hero-container { padding: 100px 1rem 40px; }
            .hero-title { font-size: 26px; letter-spacing: -0.04em; margin-bottom: 12px; line-height: 1.2; }
            .hero-subtitle { font-size: 14px; margin-bottom: 24px; line-height: 1.5; }
            
            /* Mobile Touch Scrollable Tab Bar */
            .switcher-container {
                max-width: 100%;
                overflow-x: auto;
                overflow-y: hidden;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
                padding: 4px;
                justify-content: flex-start;
            }
            .switcher-container::-webkit-scrollbar { display: none; }
            .switcher-btn {
                white-space: nowrap;
                padding: 8px 14px;
                font-size: 12px;
                min-height: 40px;
                flex-shrink: 0;
            }

            .auth-card-box { padding: 24px 14px; border-radius: 20px; }
            .form-grid { grid-template-columns: 1fr; gap: 14px; }
            
            .cap-row { grid-template-columns: 1fr; gap: 8px; padding: 1.2rem 0; }
            .cap-row-arrow { display: none; }
            .cap-row-title { font-size: 1.25rem; }
            
            /* Mobile Full-Screen Touch Drawer */
            .modal-card { 
                width: 100vw !important; 
                min-width: 100vw !important; 
                max-width: 100vw !important; 
                border-left: none; 
            }
            .modal-card-content { 
                padding: 24px 16px 140px; 
                gap: 1.2rem; 
            }
            .modal-close { 
                top: 16px; 
                right: 16px; 
                font-size: 2.2rem; 
                width: 44px; 
                height: 44px; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
            }
            .modal-title { font-size: 1.5rem; }
            .modal-phone-frame { height: 480px; max-width: 100%; border-radius: 28px; border-width: 8px; }
            .modal-phone-frame-img img { max-width: 100%; border-radius: 24px; }
            
            input { font-size: 16px; padding: 14px 16px; }
            .btn-primary { min-height: 50px; font-size: 14px; }
        }

        @media (max-width: 540px) {
            .brand-title-full { display: none; }
            .brand-title-short { display: inline; font-size: 14px; font-weight: 600; }
            .btn-nav-passwords .btn-nav-label { font-size: 10px; }
            .btn-nav-devs .btn-nav-label { font-size: 10px; }
            .btn-nav-passwords { padding: 6px 8px; }
            .btn-nav-devs { padding: 6px 8px; }
        }

        @media (max-width: 380px) {
            .btn-nav-devs .btn-nav-label { display: none; }
            .btn-nav-passwords .btn-nav-label { font-size: 9.5px; }
        }
    </style>
</head>
<body>

    <!-- Ambient Antigravity Glowing Orbs -->
    <div class="antigravity-aura-container">
        <div class="antigravity-orb antigravity-orb-1"></div>
        <div class="antigravity-orb antigravity-orb-2"></div>
        <div class="antigravity-orb antigravity-orb-3"></div>
    </div>

    <!-- Physics Kinetic Particle Canvas -->
    <canvas id="physics-canvas"></canvas>

    <!-- Section 1: Global Glassy Fixed Navigation Bar -->
    <nav class="navbar">
        <a href="/mailbot" class="brand-logo">
            <svg class="brand-logo-icon" viewBox="0 0 36 36" fill="none">
                <rect width="36" height="36" rx="10" fill="url(#botLogoGrad)"/>
                <path d="M9 11C9 9.89543 9.89543 9 11 9H25C26.1046 9 27 9.89543 27 11V21C27 22.1046 26.1046 23 25 23H14L9 27V11Z" fill="white" fill-opacity="0.95"/>
                <path d="M10 12L18 17.5L26 12" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M28 8L29.2 5.5L31.7 4.3L29.2 3.1L28 0.6L26.8 3.1L24.3 4.3L26.8 5.5L28 0.6Z" fill="#FBBF24"/>
                <defs>
                    <linearGradient id="botLogoGrad" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#25D366"/>
                        <stop offset="0.5" stop-color="#2563eb"/>
                        <stop offset="1" stop-color="#7c3aed"/>
                    </linearGradient>
                </defs>
            </svg>
            <span class="brand-title-full">WhatsApp Mail Bot AI</span>
            <span class="brand-title-short">MailBot AI</span>
        </a>

        <div class="nav-right-group">
            <!-- Global Header User Profile Avatar & Logout Dropdown -->
            <div id="header-avatar-wrapper" style="position: relative; display: none;">
                <button type="button" id="header-avatar-btn" onclick="toggleHeaderProfileDropdown(event)" style="background: none; border: none; padding: 0; cursor: pointer; display: flex; align-items: center; justify-content: center; outline: none;" title="User Account Menu">
                    <img id="header-avatar-img" src="" alt="User Avatar" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover; border: 2px solid var(--accent-light-blue); box-shadow: 0 0 10px rgba(37, 99, 235, 0.25); display: none;">
                    <div id="header-avatar-fallback" class="dev-avatar-badge" style="width: 36px; height: 36px; font-size: 0.85rem; font-weight: 600; border: 2px solid var(--accent-light-blue) !important; color: var(--text-heading); background: rgba(37, 99, 235, 0.1) !important; display: flex; align-items: center; justify-content: center; border-radius: 50%;">
                        US
                    </div>
                </button>

                <!-- Floating Profile & Logout Dropdown Menu (Directive 3: Clip-Path Shutter Panel) -->
                <div id="header-profile-dropdown" style="display: none; position: absolute; top: 48px; right: 0; min-width: 250px; background: rgba(5,5,5,0.88); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; box-shadow: 0 25px 50px rgba(0,0,0,0.6); padding: 18px; z-index: 500; text-align: left; transform-origin: top right; clip-path: inset(0% 0% 100% 0%); font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;">
                    <div style="margin-bottom: 12px;">
                        <div class="mask-item" style="overflow: hidden;">
                            <div id="header-dropdown-name" class="mask-content" style="font-size: 0.95rem; font-weight: 400; color: var(--text-heading); letter-spacing: -0.02em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: inherit;">
                                User Name
                            </div>
                        </div>
                        <div class="mask-item" style="overflow: hidden; margin-top: 4px;">
                            <div id="header-dropdown-email" class="mask-content" style="font-family: inherit !important; font-size: 0.75rem !important; color: var(--text-muted); font-weight: 400; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                user@gmail.com
                            </div>
                        </div>
                    </div>

                    <div class="mask-item" style="overflow: hidden;">
                        <div class="mask-content" style="height: 1px; background: rgba(255,255,255,0.08); margin: 10px 0;"></div>
                    </div>

                    <div class="mask-item" style="overflow: hidden;">
                        <a href="/logout" id="header-dropdown-logout" class="mask-content" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 8px 10px; border-radius: 8px; color: #ef4444; font-size: 0.85rem; font-weight: 500; text-decoration: none; transition: background 0.25s ease; box-sizing: border-box;">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transition: color 0.25s ease;">
                                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                                <polyline points="16 17 21 12 16 7"></polyline>
                                <line x1="21" y1="12" x2="9" y2="12"></line>
                            </svg>
                            <span style="transition: transform 0.25s ease, color 0.25s ease; font-family: inherit;">Log Out</span>
                        </a>
                    </div>
                </div>
            </div>

            <!-- Header Developer Quick Link Button (OKC Media Brutalist-Minimalist Access Point) -->
            <button type="button" class="btn-nav-devs" id="btn-nav-devs" onclick="openDevelopersModal()" title="View Engineering Team & Developers">
                <span class="dev-status-dot"></span>
                <span class="dev-btn-text">DEVELOPERS</span>
                <span class="dev-btn-arrow">→</span>
            </button>

            <!-- Theme Toggle Button (Light/Dark Switcher) -->
            <button type="button" class="theme-toggle-btn magnetic-btn" id="theme-toggle" onclick="toggleTheme()" title="Toggle Light/Dark Theme">
                <svg id="theme-sun-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none;">
                    <circle cx="12" cy="12" r="5"></circle>
                    <line x1="12" y1="1" x2="12" y2="3"></line>
                    <line x1="12" y1="21" x2="12" y2="23"></line>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                    <line x1="1" y1="12" x2="3" y2="12"></line>
                    <line x1="21" y1="12" x2="23" y2="12"></line>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                </svg>
                <svg id="theme-moon-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                </svg>
            </button>

            <!-- Direct Shortcut to Google App Passwords -->
            <a href="https://myaccount.google.com/apppasswords" target="_blank" class="btn-nav-passwords magnetic-btn" title="Open Google Security App Passwords in new tab">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                <span class="btn-nav-label">App Passwords ↗</span>
            </a>
        </div>
    </nav>

    <!-- Faint Drifting Particle Background Canvas -->
    <canvas id="physics-canvas"></canvas>

    <!-- Section 2: Monumental Hero Section -->
    <div class="hero-container">
        <div class="hero-brand-tag gsap-hero">
            <svg class="brand-logo-icon" style="width:20px; height:20px;" viewBox="0 0 36 36" fill="none">
                <rect width="36" height="36" rx="8" fill="url(#botLogoGrad2)"/>
                <path d="M9 11C9 9.89543 9.89543 9 11 9H25C26.1046 9 27 9.89543 27 11V21C27 22.1046 26.1046 23 25 23H14L9 27V11Z" fill="white"/>
                <path d="M10 12L18 17.5L26 12" stroke="#2563eb" stroke-width="2"/>
                <defs>
                    <linearGradient id="botLogoGrad2" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#25D366"/><stop offset="1" stop-color="#2563eb"/>
                    </linearGradient>
                </defs>
            </svg>
            Perfected Simplicity — WhatsApp Mail Bot AI
        </div>

        <h1 class="hero-title gsap-hero">Automate your emails directly inside WhatsApp</h1>
        <p class="hero-subtitle gsap-hero">Instantly draft, review, dynamically revise, and forward professional emails & PDF attachments directly from your WhatsApp messages.</p>

        <!-- Stealth Luxury Tab Switcher -->
        <div class="switcher-container gsap-hero">
            <div class="switcher-pill" id="switcher-pill"></div>
            <button type="button" class="switcher-btn active magnetic-btn" id="tab-auth" onclick="switchTab('auth')">
                Authorize Gmail
            </button>
            <button type="button" class="switcher-btn magnetic-btn" id="tab-caps" onclick="switchTab('caps')">
                Capabilities
            </button>
            <button type="button" class="switcher-btn magnetic-btn" id="tab-guide" onclick="switchTab('guide')">
                Password Guide
            </button>
        </div>

        <!-- Auth Form Panel -->
        <div class="auth-card-box form-panel gsap-hero" id="form-panel">
            <!-- Sandbox Main Wrapper for Height Morphing & Absolute Positioned Form Cross-Dissolving -->
            <div id="auth-form-wrapper" style="position: relative; width: 100%; overflow: hidden;">
                
                <!-- Sign In Form & Actions Block -->
                <div id="signin-form-block" class="auth-mode-block" style="width: 100%;">
                    <form action="/auth/submit_credentials" method="POST" id="auth-form" onsubmit="handleSubmit(event)">
                        <input type="hidden" name="phone" value="{{ phone }}">
                        
                        <div class="form-group anim-element">
                            <label>Gmail Address</label>
                            <div class="input-wrapper">
                                <input type="email" name="sender_email" id="sender_email" placeholder="you@gmail.com" value="{{ email if email else '' }}" required autocomplete="email">
                            </div>
                        </div>

                        <div class="form-group anim-element">
                            <label>Gmail App Password (16 Characters)</label>
                            <div class="input-wrapper">
                                <input type="password" id="app_password" name="app_password" placeholder="xxxx xxxx xxxx xxxx" required autocomplete="current-password">
                                <button type="button" class="password-toggle" onclick="togglePassword()">Show</button>
                            </div>
                        </div>

                        <!-- Clean Red Error Container for Failed Credentials -->
                        <div id="auth-error-box" style="display: {{ 'block' if error else 'none' }}; color: #ef4444; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 12px; padding: 12px 16px; font-size: 13px; margin-bottom: 20px; line-height: 1.5; text-align: left;">{{ error if error else '' }}</div>

                        <button type="submit" class="btn-connect magnetic-btn anim-element" id="btn-submit">
                            <span id="btn-text">Connect Gmail & Deliver Pending Email</span>
                            <div class="spinner" id="btn-spinner"></div>
                        </button>
                    </form>

                    <!-- Divider Container -->
                    <div class="divider-container anim-element" id="oauth-divider">
                        <span>OR</span>
                    </div>

                    <!-- Direct Google Cloud OAuth Route Redirect for Sign In -->
                    <a href="/login/google?phone={{ phone|urlencode }}" class="btn-google-auth magnetic-btn anim-element" title="Sign in with Google Account" id="btn-google-signin">
                        <svg width="18" height="18" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                        </svg>
                        <span>Sign in with Google Account</span>
                    </a>
                </div>

                <!-- Sign Up Form & Actions Block -->
                <div id="signup-form-block" class="auth-mode-block" style="display: none; width: 100%;">
                    <div style="padding: 10px 0;">
                        <a href="/login/google?phone={{ phone|urlencode }}" class="btn-google-auth magnetic-btn anim-element" title="Sign up with Google Account" id="btn-google-signup" style="margin-top: 0;">
                            <svg width="18" height="18" viewBox="0 0 24 24">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                            </svg>
                            <span>Sign up with Google Account</span>
                        </a>
                    </div>
                </div>

            </div>

            <!-- Subtle Mode Switcher Toggle Link for New Users -->
            <div style="margin-top: 22px; text-align: center; font-size: 13px; color: var(--text-muted);">
                <span id="mode-toggle-question">Don't have an account?</span>
                <button type="button" id="btn-mode-toggle" onclick="toggleAuthMode()" style="background: none; border: none; color: var(--accent-light-blue); font-size: 13px; font-weight: 500; cursor: pointer; text-decoration: underline; margin-left: 4px; padding: 0;">
                    Sign Up
                </button>
            </div>
        </div>

        <!-- Logged-In User Profile Dashboard Container (Directive 2: Technical Dossier Void) -->
        <div class="auth-card-box profile-panel gsap-hero" id="profile-dashboard" style="display: none; width: 100%; border: 1px solid rgba(255, 255, 255, 0.05) !important; background: transparent !important; box-shadow: none !important; border-radius: 16px !important; padding: 36px 28px; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;">
            <div style="display: flex; flex-direction: column; align-items: center; text-align: center; gap: 18px; width: 100%;">
                
                <!-- Profile Avatar Picture with Pulsing Glow Aura -->
                <div style="position: relative;" class="profile-avatar-wrapper">
                    <img id="user-profile-img" src="" alt="Profile Picture" style="width: 84px; height: 84px; border-radius: 50%; object-fit: cover; border: 1px solid rgba(0, 255, 150, 0.4); box-shadow: 0 0 20px rgba(0, 255, 150, 0.15); animation: avatarGlowPulse 4s ease-in-out infinite; display: none;">
                    <div id="user-profile-avatar-fallback" class="dev-avatar-badge" style="width: 84px; height: 84px; font-size: 1.8rem; font-weight: 600; border: 1px solid rgba(0, 255, 150, 0.4) !important; color: var(--text-heading); background: rgba(0, 255, 150, 0.08) !important; box-shadow: 0 0 20px rgba(0, 255, 150, 0.15); animation: avatarGlowPulse 4s ease-in-out infinite; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-family: inherit;">
                        US
                    </div>
                </div>

                <!-- User Details (Directive 1: Pure Sans-Serif) -->
                <div class="profile-text-wrapper">
                    <h3 id="user-profile-name" style="font-size: 26px; font-weight: 400; color: var(--text-heading); margin-bottom: 4px; letter-spacing: -0.03em; font-family: inherit;">
                        User Name
                    </h3>
                    <p id="user-profile-email" style="font-family: inherit !important; font-size: 0.85rem !important; color: var(--text-muted); font-weight: 400; margin: 0; letter-spacing: 0.01em;">
                        user@gmail.com
                    </p>
                </div>

                <!-- Status Connected Badge (Directive 2: Liquid Expand + Shimmer + Radar Pulse) -->
                <div class="status-server-tag" style="display: inline-flex; align-items: center; justify-content: flex-start; border: 1px solid rgba(0, 255, 100, 0.3) !important; background: transparent !important; color: #00ff64 !important; font-family: inherit !important; padding: 6px 18px !important; border-radius: 999px !important; margin-top: 2px; height: 32px; box-sizing: border-box; overflow: hidden; white-space: nowrap;">
                    <span class="radar-dot"></span>
                    <span class="shimmer-badge-text" style="opacity: 0; white-space: nowrap; margin-left: 8px; text-transform: uppercase; letter-spacing: 0.15em; font-weight: 500; font-size: 0.75rem; font-family: inherit;">GMAIL CONNECTED</span>
                </div>

                <p class="profile-desc-text" style="font-size: 13px; color: var(--text-body); max-width: 400px; margin-top: 4px; line-height: 1.6; font-weight: 300; font-family: inherit;">
                    Your Gmail credentials are authenticated and active. Send email briefs directly inside WhatsApp to draft and dispatch.
                </p>

                <!-- Logout Button (Directive 1: Sans-Serif Action Button) -->
                <div style="margin-top: 14px; width: 100%;">
                    <a href="/logout" id="btn-logout" class="switcher-btn magnetic-btn" style="display: inline-block; width: 100%; padding: 14px; border-radius: 999px; border: 1px solid var(--border-subtle); background: transparent; color: var(--text-heading); font-family: inherit !important; font-size: 0.8rem !important; font-weight: 500 !important; letter-spacing: 0.12em !important; text-transform: uppercase !important; text-decoration: none; text-align: center; cursor: pointer; box-sizing: border-box; transition: all 0.3s ease;">
                        Log Out
                    </a>
                </div>
            </div>
        </div>

        <!-- Editorial Row Tiles Capabilities Showcase Panel -->
        <div class="auth-card-box capabilities-panel" id="capabilities-panel">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 36px;">
                <h3 style="font-size: 26px; font-weight: 400; color:var(--text-heading); letter-spacing: -0.04em;">WhatsApp Mail Bot AI Capabilities</h3>
                <span class="mono-tag" style="color: var(--accent-light-blue);">Click row for technical dossier</span>
            </div>
            
            <div class="cap-rows-list" id="capabilities-grid">
                <div class="cap-row" onclick="openCapModal(0)">
                    <div class="cap-tag">[ INTENT ENGINE ]</div>
                    <div class="cap-row-content">
                        <div class="cap-row-title">Gemini AI Brief Analysis</div>
                        <div class="cap-row-desc">Auto-detects intent (Certificates, Invoices, Complaints) and frames executive email bodies.</div>
                    </div>
                    <div class="cap-row-arrow">→</div>
                </div>

                <div class="cap-row" onclick="openCapModal(1)">
                    <div class="cap-tag">[ BUFFER MERGE ]</div>
                    <div class="cap-row-content">
                        <div class="cap-row-title">PDF & Media Buffer Merging</div>
                        <div class="cap-row-desc">Buffers PDF files sent seconds before or after text instructions into a single unified email draft.</div>
                    </div>
                    <div class="cap-row-arrow">→</div>
                </div>

                <div class="cap-row" onclick="openCapModal(2)">
                    <div class="cap-tag">[ RECIPIENT RESOLVE ]</div>
                    <div class="cap-row-content">
                        <div class="cap-row-title">Smart Recipient Resolution</div>
                        <div class="cap-row-desc">Auto-extracts recipient emails directly from WhatsApp brief text (e.g. "forward to saakethkazipeta@gmail.com").</div>
                    </div>
                    <div class="cap-row-arrow">→</div>
                </div>

                <div class="cap-row" onclick="openCapModal(3)">
                    <div class="cap-tag">[ DYNAMIC REVISE ]</div>
                    <div class="cap-row-content">
                        <div class="cap-row-title">Dynamic WhatsApp Chat Revision</div>
                        <div class="cap-row-desc">Modify pending draft subjects & bodies on the fly by chatting in WhatsApp (e.g. "update subject to...").</div>
                    </div>
                    <div class="cap-row-arrow">→</div>
                </div>

                <div class="cap-row" onclick="openCapModal(4)">
                    <div class="cap-tag">[ TOKEN SECURITY ]</div>
                    <div class="cap-row-content">
                        <div class="cap-row-title">Multi-User Token Security</div>
                        <div class="cap-row-desc">Links 16-character Google App Passwords per phone number securely in SQLite tokens database.</div>
                    </div>
                    <div class="cap-row-arrow">→</div>
                </div>

                <div class="cap-row" onclick="openCapModal(5)">
                    <div class="cap-tag">[ INSTANT DISPATCH ]</div>
                    <div class="cap-row-content">
                        <div class="cap-row-title">Instant 1-Click Dispatch</div>
                        <div class="cap-row-desc">Review preview card in WhatsApp and reply "1" to dispatch email immediately with zero friction.</div>
                    </div>
                    <div class="cap-row-arrow">→</div>
                </div>
            </div>
        </div>

        <!-- Section 4: App Password Guide Timeline Panel -->
        <div class="auth-card-box guide-panel" id="guide-panel">
            <div style="margin-bottom: 28px;">
                <h3 style="font-size: 26px; margin-bottom: 10px; font-weight: 400; color: var(--text-heading); letter-spacing: -0.04em;">🛡️ Your Real Password is 100% Safe.</h3>
                <p style="font-size: 14px; color: var(--text-muted); line-height: 1.6; font-weight: 300;">
                    For your security, Google does not allow third-party apps to use your actual Gmail password. Instead, you must generate a secure, 16-character 'App Password' directly from Google. This acts as a safe, temporary key just for MailBot.
                </p>
            </div>
            
            <div class="guide-step">
                <div class="step-num">1</div>
                <div class="step-text">
                    <strong>Enable 2-Step Verification:</strong> Ensure 2-Step Verification is enabled on your Google Account at <a href="https://myaccount.google.com/signinoptions/two-step-verification/enroll-welcome" target="_blank" rel="noopener noreferrer">Google 2-Step Verification ↗</a>.
                </div>
            </div>

            <div class="guide-step">
                <div class="step-num">2</div>
                <div class="step-text">
                    <strong>Generate the Key:</strong> Navigate to <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer">Google Security App Passwords ↗</a> to create your unique passcode.
                </div>
            </div>

            <div class="guide-step">
                <div class="step-num">3</div>
                <div class="step-text">
                    <strong>App Name:</strong> Select "Mail" or enter <code>MailBot AI</code> as the custom app name and click <strong>Generate</strong>.
                </div>
            </div>

            <div class="guide-step">
                <div class="step-num">4</div>
                <div class="step-text">
                    <strong>Copy & Connect:</strong> Copy the 16-character code shown inside the yellow highlight box and paste it into our login form.
                </div>
            </div>

            <div style="margin-top: 36px; display: flex; flex-direction: column; gap: 14px; width: 100%;">
                <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" class="btn-connect magnetic-btn" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; width: 100%; max-width: 100%; padding: 14px 20px; border-radius: 999px; text-decoration: none; box-sizing: border-box;">
                    <span style="font-size: 15px; font-weight: 600; color: inherit;">Open Google App Passwords ↗</span>
                    <span style="font-size: 11px; opacity: 0.75; word-break: break-all; color: inherit;">myaccount.google.com/apppasswords</span>
                </a>

                <button type="button" class="switcher-btn magnetic-btn" onclick="switchTab('auth')" style="width: 100%; padding: 14px; border-radius: 999px; border: 1px solid var(--border-subtle); background: rgba(255,255,255,0.04); color: var(--text-heading); font-size: 14px; font-weight: 400; cursor: pointer; text-align: center;">
                    ← Back to Login
                </button>
            </div>
        </div>

        <!-- Section 5: Engineering Team & Developers Spotlight Panel -->
        <div class="auth-card-box developers-panel" id="developers-panel" style="display: none;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 36px;">
                <div>
                    <span class="mono-tag" style="color: var(--accent-light-blue); margin-bottom: 8px; display: inline-block;">[ SYSTEM ARCHITECTS & CREATORS ]</span>
                    <h3 style="font-size: 28px; font-weight: 400; color: var(--text-heading); letter-spacing: -0.04em;">Engineering Team</h3>
                </div>
                <div class="pulse-dot" style="width: 8px; height: 8px; background: #4ade80;"></div>
            </div>

            <div class="developer-rows-list" id="developers-rows-main">
                <!-- Lead Developer 1: Saaketh Kazipeta -->
                <a href="https://www.linkedin.com/in/kazipeta-saaketh" target="_blank" class="developer-row">
                    <div class="dev-row-main">
                        <div class="dev-row-header">
                            <div class="dev-avatar-badge">SK</div>
                            <div>
                                <h3 class="dev-row-name">Saaketh Kazipeta</h3>
                                <div class="dev-row-role">Lead System Architect & AI Engineer</div>
                            </div>
                        </div>
                        <p class="dev-row-bio">
                            Lead Developer of WhatsApp Mail Bot AI. Architect of the Gemini AI intent extraction engine, SQLite token database security, and the OKC Media editorial design system.
                        </p>
                    </div>
                    <div class="dev-row-arrow">→</div>
                </a>

                <!-- Co-Developer 2: Lalitha Subramanyam -->
                <a href="https://www.linkedin.com/in/lalitha-subramanyam-674575262/" target="_blank" class="developer-row">
                    <div class="dev-row-main">
                        <div class="dev-row-header">
                            <div class="dev-avatar-badge">LS</div>
                            <div>
                                <h3 class="dev-row-name">Lalitha Subramanyam</h3>
                                <div class="dev-row-role">Co-Developer & Technical Specialist</div>
                            </div>
                        </div>
                        <p class="dev-row-bio">
                            Co-Developer of WhatsApp Mail Bot AI. Co-architect of the 3.0-second SQLite media buffer merging protocol, Google OAuth security gateway, and real-time traffic inspection engine.
                        </p>
                    </div>
                    <div class="dev-row-arrow">→</div>
                </a>
            </div>
        </div>
    </div>

    <!-- Pure Void Technical Editorial Dossier Modal Drawer -->
    <div class="modal-overlay" id="modal-overlay" onclick="closeModalOnOverlay(event)">
        <div class="modal-card" id="modal-card" data-lenis-prevent>
            <div class="modal-card-content" id="modal-card-content">
                <!-- Massive Ultra-Thin Sans-Serif Close Button -->
                <button type="button" class="modal-close modal-stagger" onclick="closeModalDirect()">&times;</button>
                
                <div>
                    <div class="modal-badge modal-stagger" id="modal-badge">Technical Dossier</div>
                    <h2 class="modal-title modal-stagger" id="modal-title">Capability Title</h2>
                    <p class="modal-desc modal-stagger" id="modal-desc">Capability description text...</p>
                </div>

                <!-- Dynamic Phone Mockup Image / Interactive Widget Container -->
                <div class="modal-phone-container modal-stagger" id="modal-phone-container">
                    <!-- Dynamically populated via openCapModal(index) -->
                </div>
                
                <!-- Stark Left-Border Technical Fact-Box -->
                <div class="modal-fact-box modal-stagger" id="modal-fact-box">
                    <div id="modal-fact-content">
                        <!-- Dynamic Fact-Box Items -->
                    </div>
                </div>

                <!-- Detailed Workflow & Real-Time Application Breakdown -->
                <div class="modal-explanation-box modal-stagger">
                    <div class="explanation-header">Technical & Practical Workflow Breakdown</div>
                    <div id="modal-explanation-content">
                        <!-- Dynamic Step Breakdown Cards -->
                    </div>
                </div>

                <!-- Generous Bottom Scroll Buffer -->
                <div class="modal-scroll-buffer"></div>
            </div>
        </div>
    </div>

    <!-- Dedicated Engineering Team & Developers Spotlight Modal Drawer -->
    <div class="modal-overlay" id="devs-modal-overlay" onclick="closeDevsModalOnOverlay(event)">
        <div class="modal-card" id="devs-modal-card" style="max-width: 740px;" data-lenis-prevent>
            <div class="modal-card-content">
                <button type="button" class="modal-close" onclick="closeDevsModal()">&times;</button>
                
                <div style="margin-bottom: 28px;">
                    <div class="modal-badge">[ SYSTEM ARCHITECTS & CREATORS ]</div>
                    <h2 class="modal-title" style="margin-top: 6px;">Engineering Team</h2>
                    <p class="modal-desc">Core creators and system architects behind WhatsApp Mail Bot AI.</p>
                </div>

                <div class="developer-rows-list" id="devs-modal-rows">
                    <!-- Lead Developer 1: Saaketh Kazipeta -->
                    <a href="https://www.linkedin.com/in/kazipeta-saaketh" target="_blank" class="developer-row">
                        <div class="dev-row-main">
                            <div class="dev-row-header">
                                <div class="dev-avatar-badge">SK</div>
                                <div>
                                    <h3 class="dev-row-name">Saaketh Kazipeta</h3>
                                    <div class="dev-row-role">Lead System Architect & AI Engineer</div>
                                </div>
                            </div>
                            <p class="dev-row-bio">
                                Lead Developer of WhatsApp Mail Bot AI. Architect of the Gemini AI intent extraction engine, SQLite token database security, and the OKC Media editorial design system.
                            </p>
                        </div>
                        <div class="dev-row-arrow">→</div>
                    </a>

                    <!-- Co-Developer 2: Lalitha Subramanyam -->
                    <a href="https://www.linkedin.com/in/lalitha-subramanyam-674575262/" target="_blank" class="developer-row">
                        <div class="dev-row-main">
                            <div class="dev-row-header">
                                <div class="dev-avatar-badge">LS</div>
                                <div>
                                    <h3 class="dev-row-name">Lalitha Subramanyam</h3>
                                    <div class="dev-row-role">Co-Developer & Technical Specialist</div>
                                </div>
                            </div>
                            <p class="dev-row-bio">
                                Co-Developer of WhatsApp Mail Bot AI. Co-architect of the 3.0-second SQLite media buffer merging protocol, Google OAuth security gateway, and real-time traffic inspection engine.
                            </p>
                        </div>
                        <div class="dev-row-arrow">→</div>
                    </a>
                </div>
                <div class="modal-scroll-buffer"></div>
            </div>
        </div>
    </div>

    <script>
        // Auto System Theme Detection & Toggle Logic
        function initTheme() {
            const systemPrefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
            const savedTheme = localStorage.getItem('user-theme');
            const initialTheme = savedTheme || (systemPrefersLight ? 'light' : 'dark');
            setTheme(initialTheme);
        }

        function setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('user-theme', theme);
            const sunIcon = document.getElementById('theme-sun-icon');
            const moonIcon = document.getElementById('theme-moon-icon');
            if (theme === 'light') {
                if (sunIcon) sunIcon.style.display = 'block';
                if (moonIcon) moonIcon.style.display = 'none';
            } else {
                if (sunIcon) sunIcon.style.display = 'none';
                if (moonIcon) moonIcon.style.display = 'block';
            }
            if (typeof initParticles === 'function') initParticles();
        }

        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
        }

        window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', e => {
            if (!localStorage.getItem('user-theme')) {
                setTheme(e.matches ? 'light' : 'dark');
            }
        });

        // Studio Freight Lenis Smooth Scroll Setup for Main Window & High Refresh Rates (120Hz/144Hz/240Hz)
        const lenis = new Lenis({
            duration: 1.2,
            easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
            smooth: true,
            smoothTouch: false, // Hardware-accelerated GPU touch inertia at native 120Hz/144Hz
            touchMultiplier: 1.0
        });

        function raf(time) {
            lenis.raf(time);
            requestAnimationFrame(raf);
        }
        requestAnimationFrame(raf);

        // Connect Lenis with GSAP ScrollTrigger for High Refresh Rate ProMotion Displays
        gsap.registerPlugin(ScrollTrigger);
        gsap.ticker.fps(-1); // Adapts to monitor refresh rate natively (60Hz, 120Hz, 144Hz, 240Hz)
        lenis.on('scroll', ScrollTrigger.update);
        gsap.ticker.add((time) => {
            lenis.raf(time * 1000);
        });
        gsap.ticker.lagSmoothing(0);

        // Position Glider Pill on Init with Mobile Scroll Left Offset
        function initGlider() {
            const activeBtn = document.querySelector('.switcher-btn.active');
            const glider = document.getElementById('switcher-pill');
            if (activeBtn && glider) {
                const container = document.querySelector('.switcher-container');
                const containerRect = container.getBoundingClientRect();
                const btnRect = activeBtn.getBoundingClientRect();
                const scrollLeft = container.scrollLeft || 0;
                glider.style.width = `${btnRect.width}px`;
                glider.style.transform = `translate3d(${(btnRect.left - containerRect.left) + scrollLeft}px, 0, 0)`;
            }
        }

        // GSAP Hero & Editorial Row Animations
        window.addEventListener('DOMContentLoaded', () => {
            initTheme();
            initGlider();

            gsap.from('.gsap-hero', {
                y: 100,
                opacity: 0,
                duration: 1.5,
                ease: "power4.out",
                stagger: 0.18
            });

            gsap.from('.cap-row', {
                scrollTrigger: {
                    trigger: '.cap-rows-list',
                    start: 'top 85%'
                },
                y: 80,
                opacity: 0,
                duration: 1.4,
                ease: "power4.out",
                stagger: 0.12
            });
        });

        let isUserLoggedIn = false;

        // Stealth Luxury Glider Pill + GSAP Cross-Dissolve Timeline
        function switchTab(tabName) {
            const targetBtn = document.getElementById(`tab-${tabName}`);
            const glider = document.getElementById('switcher-pill');
            const container = document.querySelector('.switcher-container');
            if (!targetBtn || !glider || !container) return;
            
            const containerRect = container.getBoundingClientRect();
            const btnRect = targetBtn.getBoundingClientRect();
            const scrollLeft = container.scrollLeft || 0;
            const targetLeft = (btnRect.left - containerRect.left) + scrollLeft;
            const targetWidth = btnRect.width;

            gsap.to(glider, {
                x: targetLeft,
                width: targetWidth,
                duration: 0.6,
                ease: "power4.inOut"
            });

            document.querySelectorAll('.switcher-btn').forEach(btn => btn.classList.remove('active'));
            targetBtn.classList.add('active');

            const formPanel = document.getElementById('form-panel');
            const profilePanel = document.getElementById('profile-dashboard');
            const capPanel = document.getElementById('capabilities-panel');
            const guidePanel = document.getElementById('guide-panel');
            const devsPanel = document.getElementById('developers-panel');

            // Evaluate active panel for 'auth' tab based on login state
            const authTargetPanel = isUserLoggedIn ? profilePanel : formPanel;

            const panels = {
                'auth': authTargetPanel,
                'caps': capPanel,
                'guide': guidePanel,
                'devs': devsPanel
            };

            const targetPanel = panels[tabName];

            // Collect all main content panels to manage visibility cleanly
            const allPanels = [formPanel, profilePanel, capPanel, guidePanel, devsPanel].filter(p => p !== null);
            const visiblePanels = allPanels.filter(p => p !== targetPanel && p.style.display !== 'none' && getComputedStyle(p).display !== 'none');

            if (visiblePanels.length === 0) {
                // Ensure non-target auth panel is hidden
                if (tabName === 'auth') {
                    if (isUserLoggedIn && formPanel) formPanel.style.display = 'none';
                    if (!isUserLoggedIn && profilePanel) profilePanel.style.display = 'none';
                } else {
                    if (formPanel) formPanel.style.display = 'none';
                    if (profilePanel) profilePanel.style.display = 'none';
                }
                if (targetPanel) {
                    targetPanel.style.display = 'block';
                    gsap.fromTo(targetPanel, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: "power4.out" });
                }
                return;
            }

            const tl = gsap.timeline();
            visiblePanels.forEach(p => {
                tl.to(p, { 
                    opacity: 0, 
                    y: 10, 
                    duration: 0.25, 
                    ease: "power2.in", 
                    onComplete: () => { p.style.display = 'none'; } 
                }, 0);
            });

            // Ensure non-target auth panel is explicitly hidden
            if (tabName === 'auth') {
                if (isUserLoggedIn && formPanel) formPanel.style.display = 'none';
                if (!isUserLoggedIn && profilePanel) profilePanel.style.display = 'none';
            } else {
                if (formPanel) formPanel.style.display = 'none';
                if (profilePanel) profilePanel.style.display = 'none';
            }

            if (targetPanel) {
                tl.set(targetPanel, { display: 'block', opacity: 0, y: 20 }, ">")
                  .to(targetPanel, { opacity: 1, y: 0, duration: 0.5, ease: "power4.out" });
                if (targetPanel === profilePanel) {
                    triggerProfileDashboardGSAPEntrance();
                }
            }
        }

        // Background Particle Physics Canvas
        const canvas = document.getElementById('physics-canvas');
        const ctx = canvas.getContext('2d');
        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;

        let mouse = {
            targetX: width / 2,
            targetY: height / 2,
            x: width / 2,
            y: height / 2,
            radius: window.innerWidth < 640 ? 120 : 180
        };

        window.addEventListener('resize', () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            mouse.radius = window.innerWidth < 640 ? 120 : 180;
            initParticles();
            initGlider();
        });

        const updateMousePos = (x, y) => {
            mouse.targetX = x;
            mouse.targetY = y;
        };

        window.addEventListener('mousemove', (e) => updateMousePos(e.clientX, e.clientY));
        window.addEventListener('touchmove', (e) => {
            if (e.touches.length > 0) updateMousePos(e.touches[0].clientX, e.touches[0].clientY);
        });

        const darkColors = ['#06b6d4', '#6366f1', '#10b981', '#a855f7', '#38bdf8'];
        const lightColors = ['#2563eb', '#7c3aed', '#0d9488', '#25d366', '#0284c7'];
        let particles = [];

        function initParticles() {
            particles = [];
            const isMobile = (width < 768) || ('ontouchstart' in window);
            const count = isMobile ? 18 : Math.floor((width * height) / 8500);
            const cx = width / 2;
            const cy = height * 0.45;

            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            const colors = isLight ? lightColors : darkColors;

            for (let i = 0; i < count; i++) {
                const angle = Math.random() * Math.PI * 2;
                const dist = Math.random() * (width * 0.5);
                const px = cx + Math.cos(angle) * dist;
                const py = cy + Math.sin(angle) * (dist * 0.5);

                particles.push({
                    x: px,
                    y: py,
                    originX: px,
                    originY: py,
                    radius: Math.random() * 2.4 + 1.2,
                    color: colors[Math.floor(Math.random() * colors.length)],
                    density: (Math.random() * 22) + 8,
                    floatAngle: Math.random() * Math.PI * 2,
                    floatSpeed: Math.random() * 0.02 + 0.008
                });
            }
        }
        initParticles();

        let lastTimestamp = 0;
        function animatePhysics(timestamp) {
            if (!lastTimestamp) lastTimestamp = timestamp;
            const dt = Math.min((timestamp - lastTimestamp) / 16.667, 2.5);
            lastTimestamp = timestamp;

            mouse.x += (mouse.targetX - mouse.x) * 0.12 * dt;
            mouse.y += (mouse.targetY - mouse.y) * 0.12 * dt;

            ctx.clearRect(0, 0, width, height);

            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            const particleAlpha = isLight ? 0.65 : 0.75;
            const lineBaseAlpha = isLight ? 0.28 : 0.38;

            // Draw Constellation Connections between nearby particles
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    let dx = particles[i].x - particles[j].x;
                    let dy = particles[i].y - particles[j].y;
                    let dist = Math.sqrt(dx * dx + dy * dy);

                    if (dist < 125) {
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        let alpha = (1 - dist / 125) * lineBaseAlpha;
                        ctx.strokeStyle = isLight 
                            ? `rgba(37, 99, 235, ${alpha})` 
                            : `rgba(99, 102, 241, ${alpha})`;
                        ctx.lineWidth = 0.8;
                        ctx.stroke();
                    }
                }
            }

            for (let i = 0; i < particles.length; i++) {
                let p = particles[i];

                // Organic Antigravity Zero-G Floating Drift
                p.floatAngle += p.floatSpeed * dt;
                p.originY += Math.sin(p.floatAngle) * 0.25 * dt;
                p.originX += Math.cos(p.floatAngle) * 0.18 * dt;

                let dx = mouse.x - p.x;
                let dy = mouse.y - p.y;
                let distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < mouse.radius) {
                    let forceDirectionX = dx / distance;
                    let forceDirectionY = dy / distance;
                    let maxDistance = mouse.radius;
                    let force = (maxDistance - distance) / maxDistance;
                    let directionX = forceDirectionX * force * p.density;
                    let directionY = forceDirectionY * force * p.density;

                    p.x -= directionX * 0.5 * dt;
                    p.y -= directionY * 0.5 * dt;
                } else {
                    if (p.x !== p.originX) {
                        let dx = p.x - p.originX;
                        p.x -= dx * 0.05 * dt;
                    }
                    if (p.y !== p.originY) {
                        let dy = p.y - p.originY;
                        p.y -= dy * 0.05 * dt;
                    }
                }

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = p.color;
                ctx.globalAlpha = particleAlpha;
                ctx.fill();
            }

            requestAnimationFrame(animatePhysics);
        }
        requestAnimationFrame(animatePhysics);

        // Magnetic Cursor Pull Physics
        document.querySelectorAll('.magnetic-btn').forEach(btn => {
            btn.addEventListener('mousemove', (e) => {
                const rect = btn.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;
                btn.style.transform = `translate3d(${x * 0.22}px, ${y * 0.22}px, 0) scale(1.02)`;
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.transform = 'translate3d(0px, 0px, 0) scale(1)';
            });
        });

        // Technical Dossier Practical Real-World Fact-Box Data (100% Interactive WhatsApp UI)
        const capabilitiesData = [
            {
                title: "Gemini AI Brief Analysis Engine",
                desc: "Analyzes incoming WhatsApp messages and attached PDF documents in real time using Gemini AI to detect intent, extract recipient emails, and construct executive email drafts.",
                imgUrl: "/static/uploads/cap_0_gemini_ai_brief.png",
                waHtml: `
                    <div class="wa-date-pill">Today</div>
                    <div class="wa-msg wa-msg-out">
                        <div class="wa-pdf-card">
                            <div class="wa-pdf-icon">PDF</div>
                            <div>
                                <div class="wa-pdf-name">Certificate _ SOLID Principles Every Developer Must Know.PDF</div>
                                <div class="wa-pdf-meta">1 page • 223 kB • PDF</div>
                            </div>
                        </div>
                        <div class="wa-msg-time">9:32 AM <span class="wa-checks">✓✓</span></div>
                    </div>
                    <div class="wa-msg wa-msg-out">
                        <div>Congratulate saaketh kazipeta for achieving this by sending mail to saakethkazipeta@gmail.com</div>
                        <div class="wa-msg-time">9:32 AM <span class="wa-checks">✓✓</span></div>
                    </div>
                    <div class="wa-msg wa-msg-in">
                        <div style="font-weight:600; margin-bottom:6px; color:#111b21; font-size:13px;">📨 Email Draft Ready!</div>
                        <div style="margin-bottom:4px;">🎯 <strong>Intent:</strong> Congratulations & Recognition</div>
                        <div style="margin-bottom:4px;">👤 <strong>Recipient:</strong> Saaketh Kazipeta (<span style="color:#007aff; text-decoration:underline;">saakethkazipeta@gmail.com</span>)</div>
                        <div style="margin-bottom:4px;">📌 <strong>Subject:</strong> Congratulations on Your Outstanding Achievement!</div>
                        <div style="margin-bottom:6px;">📎 <strong>Attachment:</strong> Yes (SOLID_Principles_Cert.pdf)</div>
                        <div style="margin-top:8px; font-size:11px; color:#667781; line-height:1.5;">
                            <div>• Reply <strong>1</strong> to Send Email</div>
                            <div>• Reply <strong>NEW</strong> to Connect Another Account</div>
                        </div>
                        <div class="wa-msg-time">9:33 AM</div>
                    </div>
                `,
                factHtml: `
                    <div class="fact-item">
                        <span class="fact-label">STATUS</span>
                        <div class="fact-value">DRAFT GENERATED</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">RAW BRIEF</span>
                        <div class="fact-value">"Congratulate saaketh kazipeta for achieving this by sending mail to saakethkazipeta@gmail.com"</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">DETECTED INTENT</span>
                        <div class="fact-value">Congratulations & Recognition</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">TARGET RECIPIENT</span>
                        <div class="fact-value">saakethkazipeta@gmail.com</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">GENERATED SUBJECT</span>
                        <div class="fact-value">Congratulations on Your Outstanding Achievement!</div>
                    </div>
                    <div class="fact-action-pulse">
                        <div class="pulse-dot" style="width:6px; height:6px; background:#4ade80;"></div>
                        REPLY '1' TO DISPATCH IMMEDIATELY
                    </div>
                `,
                explainHtml: `
                    <div class="explanation-card">
                        <div class="explanation-num">01</div>
                        <div>
                            <div class="explanation-content-title">Real-Time Brief Ingestion</div>
                            <div class="explanation-content-text">When a user sends an informal message or forwards a PDF certificate on WhatsApp, our webhook immediately routes the payload to the Gemini AI engine.</div>
                        </div>
                    </div>
                    <div class="explanation-card">
                        <div class="explanation-num">02</div>
                        <div>
                            <div class="explanation-content-title">Structured Intent Extraction</div>
                            <div class="explanation-content-text">Gemini extracts target recipient emails (e.g. <code>saakethkazipeta@gmail.com</code>), identifies document context, and composes an executive email subject and body draft.</div>
                        </div>
                    </div>
                    <div class="explanation-card">
                        <div class="explanation-num">03</div>
                        <div>
                            <div class="explanation-content-title">WhatsApp Interactive Preview</div>
                            <div class="explanation-content-text">The bot sends a formatted WhatsApp preview card showing detected intent, recipient, subject, and prompt instructions to reply '1' to send.</div>
                        </div>
                    </div>
                `
            },
            {
                title: "Multi-PDF & Media Buffer Merging",
                desc: "When a PDF file is sent before or after text instructions, our 3.0-second SQLite buffer merges the file into your active email draft instead of creating duplicate requests.",
                imgUrl: "/static/uploads/cap_1_pdf_buffer_merge.png",
                waHtml: `
                    <div class="wa-date-pill">Today</div>
                    <div class="wa-encrypt-warning">🔒 Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.</div>
                    <div class="wa-msg wa-msg-out">
                        <div class="wa-pdf-card">
                            <div class="wa-pdf-icon">PDF</div>
                            <div>
                                <div class="wa-pdf-name">SOLID_Principles_Cert.pdf</div>
                                <div class="wa-pdf-meta">1 page • 223 kB</div>
                            </div>
                        </div>
                        <div class="wa-msg-time">9:37 AM <span class="wa-checks">✓✓</span></div>
                    </div>
                    <div class="wa-msg wa-msg-out">
                        <div>Send this document to saakethkazipeta@gmail.com for review.</div>
                        <div class="wa-msg-time">9:37 AM <span class="wa-checks">✓✓</span></div>
                    </div>
                    <div class="wa-msg wa-msg-in">
                        <div style="font-weight:600; margin-bottom:4px; color:#111b21;">✉️ Email Draft Ready!</div>
                        <div>🎯 <strong>Intent:</strong> Document Submission</div>
                        <div>👤 <strong>Recipient:</strong> saakethkazipeta@gmail.com</div>
                        <div>📌 <strong>Subject:</strong> Forwarded Document Attachment for Review</div>
                        <div>📎 <strong>Attachment:</strong> Yes (SOLID_Principles_Cert.pdf)</div>
                        <div style="margin-top:6px; font-size:11px; color:#8696a0;">• Reply 1 to Send Email</div>
                        <div class="wa-msg-time">9:38 AM</div>
                    </div>
                `,
                factHtml: `
                    <div class="fact-item">
                        <span class="fact-label">STATUS</span>
                        <div class="fact-value">ATTACHMENT MERGED (3.0s BUFFER)</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">BUFFERED ATTACHMENT</span>
                        <div class="fact-value">SOLID_Principles_Cert.pdf</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">LINKED DRAFT SUBJECT</span>
                        <div class="fact-value">Forwarded Document Attachment for Review</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">TARGET RECIPIENT</span>
                        <div class="fact-value">saakethkazipeta@gmail.com</div>
                    </div>
                    <div class="fact-action-pulse">
                        <div class="pulse-dot" style="width:6px; height:6px; background:#4ade80;"></div>
                        ATTACHMENT LINKED & READY FOR DISPATCH
                    </div>
                `,
                explainHtml: `
                    <div class="explanation-card">
                        <div class="explanation-num">01</div>
                        <div>
                            <div class="explanation-content-title">3.0-Second Media Window</div>
                            <div class="explanation-content-text">When media files (PDFs, images) are sent separately from text instructions, SQLite buffers media file URLs per phone key for 3.0 seconds.</div>
                        </div>
                    </div>
                    <div class="explanation-card">
                        <div class="explanation-num">02</div>
                        <div>
                            <div class="explanation-content-title">Automated Draft Binding</div>
                            <div class="explanation-content-text">Subsequent instructions automatically inherit buffered attachments (e.g., <code>SOLID_Principles_Cert.pdf</code>) into the active draft without requiring re-uploads.</div>
                        </div>
                    </div>
                `
            },
            {
                title: "Smart Recipient Resolution",
                desc: "Extracts recipient email addresses directly from brief text (e.g., 'forward to saakethkazipeta@gmail.com'). If no email is provided, resolves by person/role or uses your connected address.",
                imgUrl: "/static/uploads/cap_2_smart_recipient_resolution.png",
                waHtml: `
                    <div class="wa-date-pill">Today</div>
                    <div class="wa-encrypt-warning">🔒 Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.</div>
                    <div class="wa-msg wa-msg-out">
                        <div>Forward invoice #9401 to finance@acme.org and cc saakethkazipeta@gmail.com</div>
                        <div class="wa-msg-time">9:37 AM <span class="wa-checks">✓✓</span></div>
                    </div>
                    <div class="wa-msg wa-msg-in">
                        <div style="font-weight:600; margin-bottom:4px; color:#111b21;">✉️ Email Draft Ready!</div>
                        <div>🎯 <strong>Intent:</strong> Invoice Forwarding</div>
                        <div>👤 <strong>Recipient:</strong> finance@acme.org</div>
                        <div>👥 <strong>CC:</strong> saakethkazipeta@gmail.com</div>
                        <div>📌 <strong>Subject:</strong> Invoice #9401 Document Dispatch</div>
                        <div style="margin-top:6px; font-size:11px; color:#8696a0;">• Reply 1 to Send Email</div>
                        <div class="wa-msg-time">9:38 AM</div>
                    </div>
                `,
                factHtml: `
                    <div class="fact-item">
                        <span class="fact-label">STATUS</span>
                        <div class="fact-value">RECIPIENT RESOLVED</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">RAW INSTRUCTION</span>
                        <div class="fact-value">"Forward this invoice to finance@acme.org and cc saakethkazipeta@gmail.com"</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">PRIMARY RECIPIENT</span>
                        <div class="fact-value">finance@acme.org</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">COPIED RECIPIENT (CC)</span>
                        <div class="fact-value">saakethkazipeta@gmail.com</div>
                    </div>
                    <div class="fact-action-pulse">
                        <div class="pulse-dot" style="width:6px; height:6px; background:#4ade80;"></div>
                        CONFIRMED FOR DISPATCH
                    </div>
                `,
                explainHtml: `
                    <div class="explanation-card">
                        <div class="explanation-num">01</div>
                        <div>
                            <div class="explanation-content-title">Natural Language Entity Parsing</div>
                            <div class="explanation-content-text">Parses text instructions like <code>"forward to finance@acme.org and cc saakethkazipeta@gmail.com"</code> using regular expressions and Gemini entity recognition.</div>
                        </div>
                    </div>
                    <div class="explanation-card">
                        <div class="explanation-num">02</div>
                        <div>
                            <div class="explanation-content-title">Fallback Account Binding</div>
                            <div class="explanation-content-text">If no target email is specified in brief, resolves to your connected Gmail address or saved team recipient directory.</div>
                        </div>
                    </div>
                `
            },
            {
                title: "Dynamic WhatsApp Chat Revision",
                desc: "No need to re-send files. Reply directly in WhatsApp to dynamically revise the active pending draft's subject or body in real time before sending.",
                imgUrl: "/static/uploads/cap_3_dynamic_chat_revision.png",
                waHtml: `
                    <div class="wa-date-pill">Today</div>
                    <div class="wa-encrypt-warning">🔒 Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.</div>
                    <div class="wa-msg wa-msg-out">
                        <div>In previous document update subject to Certificate of Completion: SOLID Principles</div>
                        <div class="wa-msg-time">9:37 AM <span class="wa-checks">✓✓</span></div>
                    </div>
                    <div class="wa-msg wa-msg-in">
                        <div style="font-weight:600; margin-bottom:4px; color:#111b21;">✏️ Pending Draft Revised!</div>
                        <div>📌 <strong>Updated Subject:</strong> Certificate of Completion: SOLID Principles</div>
                        <div>👤 <strong>Recipient:</strong> saakethkazipeta@gmail.com</div>
                        <div style="margin-top:6px; font-size:11px; color:#8696a0;">• Reply 1 to Send Revised Email</div>
                        <div class="wa-msg-time">9:38 AM</div>
                    </div>
                `,
                factHtml: `
                    <div class="fact-item">
                        <span class="fact-label">STATUS</span>
                        <div class="fact-value">DRAFT REVISED</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">REVISION COMMAND</span>
                        <div class="fact-value">"In previous document update subject to Certificate of Completion: SOLID Principles"</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">UPDATED SUBJECT</span>
                        <div class="fact-value">Certificate of Completion: SOLID Principles</div>
                    </div>
                    <div class="fact-action-pulse">
                        <div class="pulse-dot" style="width:6px; height:6px; background:#4ade80;"></div>
                        REVISION SYNCED TO PENDING DRAFT
                    </div>
                `,
                explainHtml: `
                    <div class="explanation-card">
                        <div class="explanation-num">01</div>
                        <div>
                            <div class="explanation-content-title">Stateful Pending Draft Store</div>
                            <div class="explanation-content-text">Active drafts remain in pending state in <code>tokens.db</code> until explicit confirmation or timeout.</div>
                        </div>
                    </div>
                    <div class="explanation-card">
                        <div class="explanation-num">02</div>
                        <div>
                            <div class="explanation-content-title">Live Chat Subject & Body Overrides</div>
                            <div class="explanation-content-text">Replying with <code>"In previous document update subject to Certificate of Completion: SOLID Principles"</code> updates pending draft parameters in real time.</div>
                        </div>
                    </div>
                `
            },
            {
                title: "Multi-User Token Security",
                desc: "Securely links Google App Passwords per phone number in our encrypted SQLite tokens database (tokens.db). Supports multi-tenant authorization for team accounts.",
                imgUrl: "/static/uploads/cap_4_multi_user_token_security.png",
                waHtml: `
                    <div class="wa-date-pill">Today</div>
                    <div class="wa-encrypt-warning">🔒 Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.</div>
                    <div class="wa-msg wa-msg-out">
                        <div>Connect Gmail account for +919059130576</div>
                        <div class="wa-msg-time">9:37 AM <span class="wa-checks">✓✓</span></div>
                    </div>
                    <div class="wa-msg wa-msg-in">
                        <div style="font-weight:600; margin-bottom:4px; color:#111b21;">🔑 Authentication Link Generated</div>
                        <div>Please authorize your Gmail credentials via our web gateway:</div>
                        <div style="color:#007aff; text-decoration:underline; margin-top:4px;">http://localhost:5000/mailbot?phone=%2B919059130576</div>
                        <div class="wa-msg-time">9:38 AM</div>
                    </div>
                `,
                factHtml: `
                    <div class="fact-item">
                        <span class="fact-label">STATUS</span>
                        <div class="fact-value">AUTHENTICATED</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">PHONE NUMBER KEY</span>
                        <div class="fact-value">+919059130576</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">CONNECTED GMAIL</span>
                        <div class="fact-value">saakethkazipeta@gmail.com</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">CREDENTIAL STORAGE</span>
                        <div class="fact-value">SQLite Tokens Database (tokens.db)</div>
                    </div>
                    <div class="fact-action-pulse">
                        <div class="pulse-dot" style="width:6px; height:6px; background:#4ade80;"></div>
                        CREDENTIAL SECURED & ACTIVE
                    </div>
                `,
                explainHtml: `
                    <div class="explanation-card">
                        <div class="explanation-num">01</div>
                        <div>
                            <div class="explanation-content-title">SQLite Credential Encryption</div>
                            <div class="explanation-content-text">Per-user credentials (16-character Google App Passwords or OAuth refresh tokens) are bound to phone number keys in <code>tokens.db</code>.</div>
                        </div>
                    </div>
                    <div class="explanation-card">
                        <div class="explanation-num">02</div>
                        <div>
                            <div class="explanation-content-title">Multi-Tenant Tenant Isolation</div>
                            <div class="explanation-content-text">Ensures user A (+919059130576) dispatches emails strictly using user A's authenticated Gmail account without cross-tenant data leaks.</div>
                        </div>
                    </div>
                `
            },
            {
                title: "Instant 1-Click Dispatch",
                desc: "Review the generated draft preview in WhatsApp and reply with '1' to send the email and PDF attachments via Gmail SMTP instantly.",
                imgUrl: "/static/uploads/cap_5_instant_dispatch.png",
                waHtml: `
                    <div class="wa-date-pill">Today</div>
                    <div class="wa-encrypt-warning">🔒 Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.</div>
                    <div class="wa-msg wa-msg-out">
                        <div>1</div>
                        <div class="wa-msg-time">9:37 AM <span class="wa-checks">✓✓</span></div>
                    </div>
                    <div class="wa-msg wa-msg-in">
                        <div style="font-weight:600; margin-bottom:4px; color:#111b21;">🚀 Email Delivered Successfully!</div>
                        <div>Your email and attached PDF report have been sent to saakethkazipeta@gmail.com.</div>
                        <div style="font-size:10px; color:#8696a0; margin-top:4px;">Transport: Gmail SMTP SSL/TLS</div>
                        <div class="wa-msg-time">9:38 AM</div>
                    </div>
                `,
                factHtml: `
                    <div class="fact-item">
                        <span class="fact-label">STATUS</span>
                        <div class="fact-value">DISPATCH EXECUTED</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">USER CONFIRMATION</span>
                        <div class="fact-value">Signal '1' Received</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">TRANSPORT PROTOCOL</span>
                        <div class="fact-value">Gmail SMTP (Port 587 SSL/TLS)</div>
                    </div>
                    <div class="fact-item">
                        <span class="fact-label">DELIVERY STATUS</span>
                        <div class="fact-value">200 Message Sent Successfully</div>
                    </div>
                    <div class="fact-action-pulse">
                        <div class="pulse-dot" style="width:6px; height:6px; background:#4ade80;"></div>
                        TRANSACTION COMPLETE
                    </div>
                `,
                explainHtml: `
                    <div class="explanation-card">
                        <div class="explanation-num">01</div>
                        <div>
                            <div class="explanation-content-title">Single Key Confirmation ('1')</div>
                            <div class="explanation-content-text">Replying <code>1</code> in WhatsApp triggers immediate email transmission using Gmail SMTP over SSL/TLS port 587.</div>
                        </div>
                    </div>
                    <div class="explanation-card">
                        <div class="explanation-num">02</div>
                        <div>
                            <div class="explanation-content-title">Instant Webhook Status Callback</div>
                            <div class="explanation-content-text">Sends immediate success delivery notification to WhatsApp with recipient email, subject, and delivery confirmation code.</div>
                        </div>
                    </div>
                `
            }
        ];

        // Heavy Friction Drawer Slide In + Staggered GSAP Text Cascade
        function openCapModal(index) {
            const data = capabilitiesData[index];
            document.getElementById('modal-title').innerHTML = data.title;
            document.getElementById('modal-desc').innerHTML = data.desc;
            document.getElementById('modal-fact-content').innerHTML = data.factHtml;
            document.getElementById('modal-explanation-content').innerHTML = data.explainHtml;

            const phoneContainer = document.getElementById('modal-phone-container');
            if (data.imgUrl) {
                phoneContainer.innerHTML = `
                    <div class="modal-phone-frame-img">
                        <img src="${data.imgUrl}" alt="${data.title} Real-Time Example">
                    </div>
                `;
            } else {
                phoneContainer.innerHTML = `
                    <div class="modal-phone-frame">
                        <div class="phone-top-bar">
                            <span>9:41</span>
                            <div class="phone-notch"></div>
                            <div style="display:flex; gap:4px; align-items:center;">
                                <span>📶</span><span>⚡</span><span>100%</span>
                            </div>
                        </div>
                        <div class="wa-chat-header">
                            <div class="wa-back-btn">‹ 12</div>
                            <div class="wa-avatar">W</div>
                            <div class="wa-chat-info">
                                <div class="wa-chat-name">WhatsApp Mail Bot AI</div>
                                <div class="wa-chat-status">online</div>
                            </div>
                            <div class="wa-header-icons">
                                <span>📹</span>
                                <span>📞</span>
                            </div>
                        </div>
                        <div class="wa-chat-body">
                            ${data.waHtml}
                        </div>
                        <div class="wa-chat-footer">
                            <div class="wa-plus-btn">+</div>
                            <div class="wa-input-pill">Message</div>
                            <div class="wa-footer-icons">
                                <span>📄</span>
                                <span>📷</span>
                                <span>🎙️</span>
                            </div>
                        </div>
                        <div class="phone-bottom-bar">
                            <div class="phone-home-indicator"></div>
                        </div>
                    </div>
                `;
            }

            const overlay = document.getElementById('modal-overlay');
            const card = document.getElementById('modal-card');

            // Reset scroll position to top
            card.scrollTop = 0;

            overlay.style.display = 'flex';
            gsap.to(overlay, { opacity: 1, duration: 0.4, ease: "power2.out" });
            
            // Heavy friction drawer slide in (1.0s power4.out)
            gsap.fromTo(card, 
                { x: "100%" }, 
                { x: "0%", duration: 1.0, ease: "power4.out" }
            );

            // Staggered GSAP cascade of inner elements with scroller property (Directive 4)
            gsap.fromTo('.modal-stagger', 
                { y: 30, opacity: 0 },
                { 
                    y: 0, 
                    opacity: 1, 
                    duration: 0.8, 
                    ease: "power4.out", 
                    stagger: 0.1, 
                    delay: 0.2,
                    scrollTrigger: {
                        trigger: card,
                        scroller: "#modal-card",
                        start: "top 90%"
                    }
                }
            );

            // Lock main page scrolling so background page doesn't scroll
            if (typeof lenis !== 'undefined') lenis.stop();
        }

        function closeModalDirect() {
            const overlay = document.getElementById('modal-overlay');
            const card = document.getElementById('modal-card');

            gsap.to(card, { x: "100%", duration: 0.4, ease: "power3.in" });
            gsap.to(overlay, { opacity: 0, duration: 0.4, ease: "power3.in", onComplete: () => {
                overlay.style.display = 'none';
                if (typeof lenis !== 'undefined') lenis.start();
            }});
        }

        function closeModalOnOverlay(e) {
            if (e.target.id === 'modal-overlay') {
                closeModalDirect();
            }
        }

        function openDevelopersModal() {
            const overlay = document.getElementById('devs-modal-overlay');
            const card = document.getElementById('devs-modal-card');
            if (!overlay || !card) return;
            card.scrollTop = 0;
            overlay.style.display = 'flex';
            gsap.fromTo(overlay, { opacity: 0 }, { opacity: 1, duration: 0.4, ease: "power2.out" });
            gsap.fromTo(card, { x: "100%" }, { x: "0%", duration: 0.8, ease: "power4.out" });

            // Directive 3: Staggered Cascade Reveal Animation for Developer Rows
            gsap.fromTo("#devs-modal-card .developer-row",
                { y: 40, opacity: 0 },
                { y: 0, opacity: 1, duration: 1, ease: "power3.out", stagger: 0.15, delay: 0.2 }
            );

            if (typeof lenis !== 'undefined') lenis.stop();
        }

        function closeDevsModal() {
            const overlay = document.getElementById('devs-modal-overlay');
            const card = document.getElementById('devs-modal-card');
            if (!overlay || !card) return;
            gsap.to(card, { x: "100%", duration: 0.4, ease: "power3.in" });
            gsap.to(overlay, { opacity: 0, duration: 0.4, ease: "power3.in", onComplete: () => {
                overlay.style.display = 'none';
                if (typeof lenis !== 'undefined') lenis.start();
            }});
        }

        function closeDevsModalOnOverlay(e) {
            if (e.target.id === 'devs-modal-overlay') {
                closeDevsModal();
            }
        }

        function togglePassword() {
            const pwd = document.getElementById('app_password');
            const btn = document.querySelector('.password-toggle');
            if (pwd.type === 'password') {
                pwd.type = 'text';
                btn.textContent = 'Hide';
            } else {
                pwd.type = 'password';
                btn.textContent = 'Show';
            }
        }

        let isSignUpMode = false;
        let isAnimatingMode = false;

        function toggleAuthMode() {
            if (isAnimatingMode) return;
            isAnimatingMode = true;

            isSignUpMode = !isSignUpMode;
            
            const wrapper = document.getElementById('auth-form-wrapper');
            const signinBlock = document.getElementById('signin-form-block');
            const signupBlock = document.getElementById('signup-form-block');
            const toggleQuestion = document.getElementById('mode-toggle-question');
            const toggleBtn = document.getElementById('btn-mode-toggle');

            const outgoingForm = isSignUpMode ? signinBlock : signupBlock;
            const incomingForm = isSignUpMode ? signupBlock : signinBlock;

            if (toggleQuestion) toggleQuestion.textContent = isSignUpMode ? "Already have an account?" : "Don't have an account?";
            if (toggleBtn) toggleBtn.textContent = isSignUpMode ? "Sign In" : "Sign Up";

            if (typeof gsap !== 'undefined' && wrapper && outgoingForm && incomingForm) {
                // Directive 1 & 2: Measure current wrapper height
                const currentHeight = wrapper.getBoundingClientRect().height || wrapper.offsetHeight;
                wrapper.style.height = currentHeight + 'px';
                wrapper.style.overflow = 'hidden';

                // Step 1: Position incoming form absolutely, display: block, opacity: 0 to measure newHeight
                incomingForm.style.position = 'absolute';
                incomingForm.style.top = '0';
                incomingForm.style.left = '0';
                incomingForm.style.width = '100%';
                incomingForm.style.display = 'block';
                incomingForm.style.opacity = '0';
                incomingForm.style.pointerEvents = 'none';

                outgoingForm.style.position = 'absolute';
                outgoingForm.style.top = '0';
                outgoingForm.style.left = '0';
                outgoingForm.style.width = '100%';
                outgoingForm.style.pointerEvents = 'none';

                // Step 2: Measure newHeight
                const newHeight = incomingForm.getBoundingClientRect().height || incomingForm.offsetHeight;

                // Step 3: Animate wrapper height to match new form (power4.inOut, duration 0.6s)
                gsap.to(wrapper, {
                    height: newHeight,
                    duration: 0.6,
                    ease: "power4.inOut"
                });

                // Directive 3: Outgoing Form (y: -20, opacity: 0, power3.in, duration 0.4s)
                gsap.to(outgoingForm, {
                    y: -20,
                    opacity: 0,
                    duration: 0.4,
                    ease: "power3.in",
                    onComplete: () => {
                        outgoingForm.style.display = 'none';
                        outgoingForm.style.position = '';
                        outgoingForm.style.top = '';
                        outgoingForm.style.left = '';
                        outgoingForm.style.width = '';
                        outgoingForm.style.pointerEvents = '';
                    }
                });

                // Directive 3: Incoming Form (y: 20 -> 0, opacity: 1, power4.out, duration 0.6s, delay 0.2s)
                gsap.fromTo(incomingForm,
                    { y: 20, opacity: 0 },
                    {
                        y: 0,
                        opacity: 1,
                        duration: 0.6,
                        ease: "power4.out",
                        delay: 0.2,
                        onComplete: () => {
                            incomingForm.style.position = 'relative';
                            incomingForm.style.top = '';
                            incomingForm.style.left = '';
                            incomingForm.style.width = '100%';
                            incomingForm.style.pointerEvents = '';
                            wrapper.style.height = 'auto';
                            wrapper.style.overflow = 'visible';
                            isAnimatingMode = false;
                        }
                    }
                );

                // Directive 4: Micro-Stagger (stagger: 0.05, ease: "power3.out", delay: 0.35s)
                const incomingElements = incomingForm.querySelectorAll('.anim-element, .form-group, .btn-connect, .btn-google-auth, .divider-container');
                if (incomingElements.length > 0) {
                    gsap.fromTo(incomingElements,
                        { y: 15, opacity: 0 },
                        {
                            y: 0,
                            opacity: 1,
                            duration: 0.5,
                            stagger: 0.05,
                            ease: "power3.out",
                            delay: 0.35
                        }
                    );
                }
            } else {
                outgoingForm.style.display = 'none';
                incomingForm.style.display = 'block';
                isAnimatingMode = false;
            }
        }

        async function handleSubmit(e) {
            e.preventDefault();
            const btnText = document.getElementById('btn-text');
            const spinner = document.getElementById('btn-spinner');
            const submitBtn = document.getElementById('btn-submit');
            const errorBox = document.getElementById('auth-error-box');

            const phoneInput = document.querySelector('input[name="phone"]');
            const phone = phoneInput ? phoneInput.value : '';
            const senderEmailInput = document.getElementById('sender_email');
            const senderEmail = senderEmailInput ? senderEmailInput.value.trim() : '';
            const appPasswordInput = document.getElementById('app_password');
            const appPassword = appPasswordInput ? appPasswordInput.value.trim() : '';

            if (!senderEmail || !appPassword) {
                if (errorBox) {
                    errorBox.textContent = "Please fill in all required fields.";
                    errorBox.style.display = "block";
                }
                return;
            }

            if (errorBox) errorBox.style.display = "none";
            if (btnText) btnText.style.display = 'none';
            if (spinner) spinner.style.display = 'block';
            if (submitBtn) submitBtn.disabled = true;

            try {
                const response = await fetch('/api/verify-app-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        phone: phone,
                        email: senderEmail,
                        sender_email: senderEmail,
                        app_password: appPassword,
                        is_new_user: isSignUpMode
                    })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    const searchParams = new URLSearchParams({ email: senderEmail, phone: phone });
                    window.location.href = '/auth/submit_credentials_success?' + searchParams.toString();
                } else {
                    if (btnText) btnText.style.display = 'block';
                    if (spinner) spinner.style.display = 'none';
                    if (submitBtn) submitBtn.disabled = false;

                    if (errorBox) {
                        errorBox.textContent = data.error || "Invalid email or App Password. Please ensure 2-Step Verification is active and a 16-character App Password is used.";
                        errorBox.style.display = "block";
                    }
                }
            } catch (err) {
                if (btnText) btnText.style.display = 'block';
                if (spinner) spinner.style.display = 'none';
                if (submitBtn) submitBtn.disabled = false;

                if (errorBox) {
                    errorBox.textContent = "Invalid email or App Password. Please ensure 2-Step Verification is active and a 16-character App Password is used.";
                    errorBox.style.display = "block";
                }
            }
        }

        // OKC Media Heavy-Friction Magnetic Physics & Data Reveal for Developers Button
        document.addEventListener('DOMContentLoaded', () => {
            const devBtn = document.getElementById('btn-nav-devs');
            if (devBtn) {
                const devText = devBtn.querySelector('.dev-btn-text');
                const devArrow = devBtn.querySelector('.dev-btn-arrow');
                const isTouchDevice = ('ontouchstart' in window) || (window.innerWidth <= 768);

                if (!isTouchDevice && typeof gsap !== 'undefined') {
                    devBtn.addEventListener('mousemove', (e) => {
                        const rect = devBtn.getBoundingClientRect();
                        const centerX = rect.left + rect.width / 2;
                        const centerY = rect.top + rect.height / 2;
                        const deltaX = e.clientX - centerX;
                        const deltaY = e.clientY - centerY;

                        // Directive 2: Magnetic trailing with heavy friction (x: deltaX * 0.4, y: deltaY * 0.4, duration: 1, ease: power3.out)
                        gsap.to(devBtn, {
                            x: deltaX * 0.4,
                            y: deltaY * 0.4,
                            duration: 1,
                            ease: "power3.out"
                        });
                    });

                    devBtn.addEventListener('mouseenter', () => {
                        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
                        // Directive 3: Hairline border brightens to theme accent/contrast color
                        gsap.to(devBtn, {
                            borderColor: isLight ? "rgba(15, 23, 42, 0.4)" : "rgba(255, 255, 255, 0.4)",
                            color: isLight ? "#0f172a" : "#ffffff",
                            duration: 0.4,
                            ease: "power2.out"
                        });

                        // Directive 3: Text letter-spacing expands smoothly to 0.15em & compositionally shifts left (-2px)
                        if (devText) {
                            gsap.to(devText, {
                                letterSpacing: "0.15em",
                                x: -2,
                                duration: 0.4,
                                ease: "power2.out"
                            });
                        }

                        // Directive 3: Arrow slides right by 5px and fades to opacity 1
                        if (devArrow) {
                            gsap.to(devArrow, {
                                x: 5,
                                opacity: 1,
                                duration: 0.4,
                                ease: "power2.out"
                            });
                        }
                    });

                    devBtn.addEventListener('mouseleave', () => {
                        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
                        // Directive 2: Snap back to origin with elastic spring physics (elastic.out(1, 0.3))
                        gsap.to(devBtn, {
                            x: 0,
                            y: 0,
                            borderColor: isLight ? "rgba(0, 0, 0, 0.12)" : "rgba(255, 255, 255, 0.15)",
                            color: isLight ? "#0f172a" : "rgba(255, 255, 255, 0.85)",
                            duration: 1,
                            ease: "elastic.out(1, 0.3)"
                        });

                        if (devText) {
                            gsap.to(devText, {
                                letterSpacing: "0.1em",
                                x: 0,
                                duration: 0.6,
                                ease: "power3.out"
                            });
                        }

                        if (devArrow) {
                            gsap.to(devArrow, {
                                x: 0,
                                opacity: 0.6,
                                duration: 0.6,
                                ease: "power3.out"
                            });
                        }
                    });
                }
            }

            // Directive 3: Editorial Row Hover Physics for Developer Profiles
            document.querySelectorAll('.developer-row').forEach(row => {
                const mainText = row.querySelector('.dev-row-main');
                const arrow = row.querySelector('.dev-row-arrow');

                row.addEventListener('mouseenter', () => {
                    if (mainText) {
                        gsap.to(mainText, { x: 10, duration: 0.4, ease: "power2.out" });
                    }
                    if (arrow) {
                        gsap.to(arrow, { opacity: 1, x: 0, duration: 0.4, ease: "power2.out" });
                    }
                });

                row.addEventListener('mouseleave', () => {
                    if (mainText) {
                        gsap.to(mainText, { x: 0, duration: 0.4, ease: "power2.out" });
                    }
                    if (arrow) {
                        gsap.to(arrow, { opacity: 0, x: -10, duration: 0.4, ease: "power2.out" });
                    }
                });
            });

            // Check current logged-in user profile on load
            checkCurrentUser();
        });

        function toggleHeaderProfileDropdown(event) {
            if (event) event.stopPropagation();
            const dropdown = document.getElementById('header-profile-dropdown');
            if (!dropdown) return;
            const isHidden = dropdown.style.display === 'none' || getComputedStyle(dropdown).display === 'none';
            if (isHidden) {
                dropdown.style.display = 'block';
                const maskContents = dropdown.querySelectorAll('.mask-content');

                gsap.killTweensOf([dropdown, maskContents]);

                gsap.fromTo(dropdown,
                    { clipPath: "inset(0% 0% 100% 0%)" },
                    { clipPath: "inset(0% 0% 0% 0%)", duration: 0.6, ease: "power4.inOut" }
                );

                if (maskContents.length > 0) {
                    gsap.fromTo(maskContents,
                        { y: "100%", opacity: 0 },
                        { y: "0%", opacity: 1, duration: 0.5, ease: "power3.out", stagger: 0.05, delay: 0.12 }
                    );
                }
            } else {
                gsap.to(dropdown, {
                    clipPath: "inset(0% 0% 100% 0%)",
                    duration: 0.4,
                    ease: "power4.inOut",
                    onComplete: () => { dropdown.style.display = 'none'; }
                });
            }
        }

        // Attach hover listener for Log Out button inside Dropdown (Directive 1)
        window.addEventListener('DOMContentLoaded', () => {
            const logoutLink = document.getElementById('header-dropdown-logout');
            if (logoutLink) {
                const spanElem = logoutLink.querySelector('span');
                const svgElem = logoutLink.querySelector('svg');
                logoutLink.addEventListener('mouseenter', () => {
                    if (spanElem) gsap.to(spanElem, { x: 5, color: '#ff4444', duration: 0.3, ease: "power2.out" });
                    if (svgElem) gsap.to(svgElem, { color: '#ff4444', duration: 0.3, ease: "power2.out" });
                    logoutLink.style.background = 'rgba(255, 68, 68, 0.08)';
                });
                logoutLink.addEventListener('mouseleave', () => {
                    if (spanElem) gsap.to(spanElem, { x: 0, color: '#ef4444', duration: 0.3, ease: "power2.out" });
                    if (svgElem) gsap.to(svgElem, { color: '#ef4444', duration: 0.3, ease: "power2.out" });
                    logoutLink.style.background = 'transparent';
                });
            }
        });

        document.addEventListener('click', (e) => {
            const wrapper = document.getElementById('header-avatar-wrapper');
            const dropdown = document.getElementById('header-profile-dropdown');
            if (dropdown && wrapper && !wrapper.contains(e.target)) {
                if (dropdown.style.display !== 'none' && getComputedStyle(dropdown).display !== 'none') {
                    gsap.to(dropdown, {
                        clipPath: "inset(0% 0% 100% 0%)",
                        duration: 0.4,
                        ease: "power4.inOut",
                        onComplete: () => { dropdown.style.display = 'none'; }
                    });
                }
            }
        });

        // Staggered Entrance Animation for Main Authorized Tab (Directive 2: Liquid Expand Badge + Directive 3: Cascade)
        function triggerProfileDashboardGSAPEntrance() {
            const panel = document.getElementById('profile-dashboard');
            if (!panel) return;

            const avatar = panel.querySelector('.profile-avatar-wrapper');
            const textGroup = panel.querySelector('.profile-text-wrapper');
            const badge = panel.querySelector('.status-server-tag');
            const badgeText = panel.querySelector('.shimmer-badge-text');
            const desc = panel.querySelector('.profile-desc-text');
            const logoutBtn = panel.querySelector('#btn-logout');

            const tl = gsap.timeline();

            if (avatar) {
                tl.fromTo(avatar,
                    { scale: 0.8, opacity: 0 },
                    { scale: 1, opacity: 1, duration: 0.8, ease: "back.out(1.5)" }
                );
            }

            if (textGroup) {
                tl.fromTo(textGroup,
                    { y: 20, opacity: 0 },
                    { y: 0, opacity: 1, duration: 0.8, ease: "power3.out" },
                    "-=0.4"
                );
            }

            // Directive 2: Liquid Expand GSAP Animation on Server Status Badge
            if (badge) {
                gsap.set(badge, { width: 32, paddingLeft: 10, paddingRight: 10 });
                if (badgeText) gsap.set(badgeText, { opacity: 0, x: -10 });

                tl.to(badge, {
                    width: "auto",
                    paddingLeft: 18,
                    paddingRight: 18,
                    duration: 0.7,
                    ease: "power4.inOut"
                }, "-=0.3")
                .to(badgeText, {
                    opacity: 1,
                    x: 0,
                    duration: 0.4,
                    ease: "power2.out"
                }, "-=0.2");
            }

            const remainingElements = [desc, logoutBtn].filter(Boolean);
            if (remainingElements.length > 0) {
                tl.fromTo(remainingElements,
                    { y: 20, opacity: 0 },
                    { y: 0, opacity: 1, duration: 0.8, ease: "power3.out", stagger: 0.1 },
                    "-=0.3"
                );
            }
        }

        async function checkCurrentUser() {
            try {
                const urlParams = new URLSearchParams(window.location.search);
                const phone = urlParams.get('phone') || '';
                const statusParam = urlParams.get('status') || '';
                const response = await fetch('/api/current-user?phone=' + encodeURIComponent(phone) + (statusParam ? '&status=' + encodeURIComponent(statusParam) : ''));
                const data = await response.json();

                const authPanel = document.getElementById('form-panel');
                const profilePanel = document.getElementById('profile-dashboard');
                const headerWrapper = document.getElementById('header-avatar-wrapper');
                const headerImg = document.getElementById('header-avatar-img');
                const headerFallback = document.getElementById('header-avatar-fallback');
                const headerName = document.getElementById('header-dropdown-name');
                const headerEmail = document.getElementById('header-dropdown-email');
                const headerLogout = document.getElementById('header-dropdown-logout');

                if (data.logged_in && data.user) {
                    isUserLoggedIn = true;
                    const user = data.user;
                    const nameElem = document.getElementById('user-profile-name');
                    const emailElem = document.getElementById('user-profile-email');
                    const imgElem = document.getElementById('user-profile-img');
                    const fallbackElem = document.getElementById('user-profile-avatar-fallback');
                    const logoutBtn = document.getElementById('btn-logout');

                    if (nameElem) nameElem.textContent = user.name || user.email.split('@')[0];
                    if (emailElem) emailElem.textContent = user.email;

                    if (headerName) headerName.textContent = user.name || user.email.split('@')[0];
                    if (headerEmail) headerEmail.textContent = user.email;

                    if (user.picture && imgElem) {
                        imgElem.onerror = function() {
                            this.style.display = 'none';
                            if (fallbackElem) fallbackElem.style.display = 'flex';
                        };
                        imgElem.onload = function() {
                            this.style.display = 'block';
                            if (fallbackElem) fallbackElem.style.display = 'none';
                        };
                        imgElem.src = user.picture;
                    } else if (fallbackElem) {
                        const initials = (user.name || user.email).substring(0, 2).toUpperCase();
                        fallbackElem.textContent = initials;
                        fallbackElem.style.display = 'flex';
                        if (imgElem) imgElem.style.display = 'none';
                    }

                    if (user.picture && headerImg) {
                        headerImg.onerror = function() {
                            this.style.display = 'none';
                            if (headerFallback) headerFallback.style.display = 'flex';
                        };
                        headerImg.onload = function() {
                            this.style.display = 'block';
                            if (headerFallback) headerFallback.style.display = 'none';
                        };
                        headerImg.src = user.picture;
                    } else if (headerFallback) {
                        const initials = (user.name || user.email).substring(0, 2).toUpperCase();
                        headerFallback.textContent = initials;
                        headerFallback.style.display = 'flex';
                        if (headerImg) headerImg.style.display = 'none';
                    }

                    if (headerWrapper) headerWrapper.style.display = 'block';

                    const userPhone = user.phone || phone;
                    if (logoutBtn) {
                        logoutBtn.href = '/logout' + (userPhone ? '?phone=' + encodeURIComponent(userPhone) : '');
                    }
                    if (headerLogout) {
                        headerLogout.href = '/logout' + (userPhone ? '?phone=' + encodeURIComponent(userPhone) : '');
                    }

                    const activeTabBtn = document.querySelector('.switcher-btn.active');
                    const isAuthTabActive = !activeTabBtn || activeTabBtn.id === 'tab-auth';

                    if (isAuthTabActive) {
                        if (authPanel) authPanel.style.display = 'none';
                        if (profilePanel) {
                            profilePanel.style.display = 'block';
                            triggerProfileDashboardGSAPEntrance();
                        }
                    } else {
                        if (authPanel) authPanel.style.display = 'none';
                        if (profilePanel) profilePanel.style.display = 'none';
                    }
                } else {
                    isUserLoggedIn = false;
                    if (headerWrapper) headerWrapper.style.display = 'none';
                    const activeTabBtn = document.querySelector('.switcher-btn.active');
                    const isAuthTabActive = !activeTabBtn || activeTabBtn.id === 'tab-auth';

                    if (isAuthTabActive) {
                        if (profilePanel) profilePanel.style.display = 'none';
                        if (authPanel) authPanel.style.display = 'block';
                    } else {
                        if (authPanel) authPanel.style.display = 'none';
                        if (profilePanel) profilePanel.style.display = 'none';
                    }
                }
            } catch (err) {
                isUserLoggedIn = false;
                const headerWrapper = document.getElementById('header-avatar-wrapper');
                if (headerWrapper) headerWrapper.style.display = 'none';
                console.error("Error checking current user:", err);
            }
        }
    </script>
</body>
</html>
"""

SUCCESS_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gmail Connected — WhatsApp Mail Bot AI</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #000000;
            color: #ffffff;
            min-height: 100vh;
            height: 100vh;
            width: 100vw;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            overflow: hidden;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
            position: relative;
            padding: 24px;
        }

        /* Ambient Glowing Aura Background Orbs */
        .aura-container {
            position: absolute;
            width: 100%;
            height: 100%;
            top: 0;
            left: 0;
            overflow: hidden;
            z-index: 1;
            pointer-events: none;
        }
        .aura-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(120px);
            opacity: 0.25;
        }
        .aura-orb-1 {
            width: 600px;
            height: 600px;
            top: -150px;
            left: 50%;
            transform: translateX(-50%);
            background: radial-gradient(circle, rgba(37, 211, 102, 0.4) 0%, rgba(37, 99, 235, 0.15) 70%, transparent 100%);
        }

        .success-wrapper {
            position: relative;
            z-index: 2;
            display: flex;
            flex-direction: column;
            align-items: center;
            max-width: 640px;
            width: 100%;
        }

        /* Checkmark Style */
        .success-checkmark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 3.5rem;
            color: #4ade80;
            text-shadow: 0 0 35px rgba(74, 222, 128, 0.45);
            line-height: 1;
            margin-bottom: 1rem;
        }

        /* Monumental Title */
        .success-title {
            font-size: clamp(2.5rem, 5vw, 4rem);
            font-weight: 400;
            letter-spacing: -0.04em;
            color: #ffffff;
            line-height: 1.1;
            margin-bottom: 0.8rem;
        }

        /* Success Message */
        .success-msg {
            font-size: 1.1rem;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.85);
            text-shadow: 0 0 20px rgba(74, 222, 128, 0.2);
            line-height: 1.5;
            margin-bottom: 2rem;
            max-width: 500px;
        }

        /* Technical Fact-Box Data Display */
        .technical-fact-box {
            border-left: 1px solid rgba(255, 255, 255, 0.15);
            padding: 1.4rem 1.8rem;
            text-align: left;
            margin: 1.5rem 0 2.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 0 16px 16px 0;
            width: 100%;
            max-width: 460px;
        }

        .fact-item {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .fact-label {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
            font-size: 0.75rem;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.4);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .fact-value {
            font-size: 1rem;
            color: #ffffff;
            font-weight: 400;
            word-break: break-all;
        }

        /* Exit Interaction Pulse Text */
        .exit-text {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.35);
            letter-spacing: 0.02em;
            animation: slowPulse 3.5s ease-in-out infinite alternate;
        }

        @keyframes slowPulse {
            0% { opacity: 0.25; transform: scale(0.99); }
            100% { opacity: 0.65; transform: scale(1.01); }
        }
    </style>
</head>
<body>

    <div class="aura-container">
        <div class="aura-orb aura-orb-1"></div>
    </div>

    <div class="success-wrapper">
        <span class="success-checkmark gsap-stagger">✓</span>
        <h1 class="success-title gsap-stagger">Gmail Connected!</h1>
        <p class="success-msg gsap-stagger">Pending email & attachment delivered automatically!</p>

        <!-- Technical Fact-Box -->
        <div class="technical-fact-box gsap-stagger">
            <div class="fact-item">
                <div class="fact-label">ACTIVE GMAIL</div>
                <div class="fact-value">{{ email }}</div>
            </div>
            <div class="fact-item">
                <div class="fact-label">LINKED WHATSAPP NUMBER</div>
                <div class="fact-value">{{ phone }}</div>
            </div>
        </div>

        <p class="exit-text gsap-stagger" style="margin-bottom: 8px;">
            Redirecting to your dashboard in <span id="redirect-countdown" style="font-weight: 600; color: #60a5fa;">3</span> seconds...
        </p>
        <a href="/mailbot?phone={{ phone }}" class="gsap-stagger" style="color: #60a5fa; text-decoration: underline; font-size: 14px; font-weight: 500; display: inline-block; margin-top: 4px;">
            Go to Dashboard →
        </a>
    </div>

    <script>
        window.addEventListener('DOMContentLoaded', () => {
            gsap.from('.gsap-stagger', {
                y: 40,
                opacity: 0,
                duration: 1.5,
                ease: "power4.out",
                stagger: 0.15
            });

            if (typeof confetti === 'function') {
                confetti({ particleCount: 60, spread: 70, origin: { y: 0.6 }, colors: ['#25D366', '#60a5fa', '#a855f7'] });
            }

            let timeLeft = 3;
            const countdownElem = document.getElementById('redirect-countdown');
            const targetUrl = "/mailbot" + ("{{ phone }}" ? "?phone=" + encodeURIComponent("{{ phone }}") : "");

            const interval = setInterval(() => {
                timeLeft -= 1;
                if (countdownElem) countdownElem.textContent = timeLeft;
                if (timeLeft <= 0) {
                    clearInterval(interval);
                    window.location.href = targetUrl;
                }
            }, 1000);
        });
    </script>
</body>
</html>
"""

import json
from google_auth_oauthlib.flow import Flow
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def get_oauth_redirect_uri(path="/oauth2callback"):
    """
    Constructs Web OAuth Redirect URI dynamically.
    Prefers active ngrok tunnel URL (e.g. https://gloater-chess-displease.ngrok-free.dev/oauth2callback)
    with fallback to local host.
    """
    base_url = get_base_url().rstrip('/')
    if "ngrok" in base_url and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://")
    return f"{base_url}{path}"

def get_client_secrets():
    client_id = os.getenv("GOOGLE_CLIENT_ID", "674584527266-djfif6gqilv7qq93bkuid5ptr272hej4.apps.googleusercontent.com")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if os.path.exists("credentials.json"):
        try:
            with open("credentials.json", "r") as f:
                data = json.load(f)
                info = data.get("web") or data.get("installed") or {}
                client_id = info.get("client_id", client_id)
                client_secret = info.get("client_secret", client_secret)
        except Exception as e:
            print("Error reading credentials.json:", e)
    return client_id, client_secret

@app.route("/login/google", methods=["GET"])
@app.route("/auth/google", methods=["GET"])
def google_auth_redirect():
    phone = db.clean_phone_number(request.args.get("phone", ""))
    session_state = json.dumps({"phone": phone})
    redirect_uri = get_oauth_redirect_uri("/oauth2callback")
    client_id, _ = get_client_secrets()
    
    encoded_redirect = urllib.parse.quote(redirect_uri, safe='')
    encoded_state = urllib.parse.quote(session_state, safe='')
    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.send"
    ]
    scope_str = urllib.parse.quote(" ".join(scopes), safe='')
    
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"response_type=code&client_id={client_id}&"
        f"redirect_uri={encoded_redirect}&"
        f"scope={scope_str}&"
        f"access_type=offline&prompt=consent&state={encoded_state}"
    )
    return redirect(google_auth_url)


def register_user_email(email: str):
    """
    Registers a user's email into users.json tracking storage.
    """
    if not email:
        return
    email_clean = email.strip().lower()
    users_file = os.path.join(os.path.dirname(__file__), "users.json")
    registered_list = []
    if os.path.exists(users_file):
        try:
            with open(users_file, "r", encoding="utf-8") as f:
                registered_list = json.load(f)
                if not isinstance(registered_list, list):
                    registered_list = []
        except Exception:
            registered_list = []
    
    if email_clean not in [str(e).lower() for e in registered_list]:
        registered_list.append(email_clean)
        try:
            with open(users_file, "w", encoding="utf-8") as f:
                json.dump(registered_list, f, indent=2)
        except Exception as e:
            print("Error writing users.json:", e)


def is_user_registered(email: str) -> bool:
    """
    Checks if an email is registered via users.json or SQLite DB.
    """
    if not email:
        return False
    email_clean = email.strip().lower()

    # 1. Check users.json
    users_file = os.path.join(os.path.dirname(__file__), "users.json")
    if os.path.exists(users_file):
        try:
            with open(users_file, "r", encoding="utf-8") as f:
                registered_list = json.load(f)
                if isinstance(registered_list, list):
                    if email_clean in [str(e).lower() for e in registered_list]:
                        return True
        except Exception:
            pass

    # 2. Check SQLite user_accounts database table
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT active_email FROM user_accounts")
            rows = cursor.fetchall()
            for r in rows:
                if r["active_email"] and r["active_email"].strip().lower() == email_clean:
                    return True
    except Exception:
        pass

    return False


@app.route("/oauth2callback", methods=["GET"])
@app.route("/auth/google/callback", methods=["GET"])
def google_auth_callback():
    phone = ""
    state_raw = request.args.get("state", "")
    if state_raw:
        try:
            state_data = json.loads(state_raw)
            phone = db.clean_phone_number(state_data.get("phone", ""))
        except Exception:
            pass

    code = request.args.get("code")
    error_arg = request.args.get("error")
    if error_arg:
        return redirect("/mailbot?status=error&message=" + urllib.parse.quote(error_arg))

    if code:
        try:
            client_id, client_secret = get_client_secrets()
            redirect_uri = get_oauth_redirect_uri("/oauth2callback")

            # Direct Web Client OAuth 2.0 token exchange (stateless & immune to PKCE verifier mismatch)
            token_url = "https://oauth2.googleapis.com/token"
            token_payload = {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }

            token_res = requests.post(token_url, data=token_payload, timeout=12)
            token_json = token_res.json()

            if "error" in token_json:
                error_msg = token_json.get("error_description") or token_json.get("error")
                print(f"[OAuth Exchange Error] {error_msg}")
                return redirect("/mailbot?status=error&message=" + urllib.parse.quote(str(error_msg)))

            access_token = token_json.get("access_token")
            refresh_token = token_json.get("refresh_token", "")

            # Fetch authenticated user profile data (name, email, picture)
            user_info_res = requests.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            user_info_data = user_info_res.json()
            user_email = user_info_data.get("email", "connected-user@gmail.com")
            user_name = user_info_data.get("name") or user_info_data.get("given_name") or user_email.split("@")[0]
            user_picture = user_info_data.get("picture", "")

            # Register user email in tracking storage
            register_user_email(user_email)

            # Store user profile in Flask session
            session["user"] = {
                "name": user_name,
                "email": user_email,
                "picture": user_picture,
                "phone": phone
            }

            creds_dict = {
                "token": access_token,
                "refresh_token": refresh_token,
                "token_uri": token_url,
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile", "openid"],
                "sender_email": user_email,
                "name": user_name,
                "picture": user_picture
            }

            # Save credentials to SQLite DB and token.json
            db.save_user_credentials(phone or "+919059130576", user_email, creds_dict, auth_type="oauth")
            try:
                with open("token.json", "w") as tf:
                    json.dump(creds_dict, tf, indent=2)
            except Exception as te:
                print("Error writing token.json:", te)

            # Deliver any pending draft automatically & notify user via WhatsApp
            target_phone = phone or "+919059130576"
            link_msg = (
                "✅ *Gmail Account Successfully Linked!*\n\n"
                f"📱 *Phone Number*: `{target_phone}`\n"
                f"📧 *Linked Email*: `{user_email}`\n\n"
                "💡 *Available WhatsApp Commands*:\n"
                "• Send any text brief or document to draft and send emails.\n"
                "• Reply *LOGOUT* (or *UNLINK*, *EXIT*) to disconnect your account directly from WhatsApp.\n"
                "• Reply *NEW* to connect a different Gmail account."
            )

            pending = db.get_pending_draft(target_phone)
            if pending:
                try:
                    send_email_with_user_creds(
                        user_info=creds_dict,
                        to_email=pending["target_email"],
                        subject=pending["subject"],
                        body=pending["body"],
                        media_url=pending.get("media_url"),
                        file_name=pending.get("file_name")
                    )
                    db.clear_pending_draft(target_phone)
                    link_msg += f"\n\n🚀 *Pending Email Delivered* to `{pending['target_email']}`! (Subject: '{pending['subject']}')"
                except Exception as ex:
                    print("Error delivering draft via OAuth:", ex)

            try:
                send_whatsapp_notification(target_phone, link_msg)
            except Exception as ne:
                print("Error sending OAuth WhatsApp notification:", ne)

            return redirect(f"/mailbot?status=connected&email={urllib.parse.quote(user_email)}&phone={urllib.parse.quote(phone or '+919059130576')}")
        except Exception as e:
            print("OAuth Callback Exception:", e)
            return redirect("/mailbot?status=error&message=" + urllib.parse.quote(str(e)))

    status_param = request.args.get("status", "")
    if status_param == "connected":
        return redirect(f"/mailbot?status=connected&phone={urllib.parse.quote(phone)}")

    return redirect("/mailbot")


@app.route("/api/current-user", methods=["GET"])
def current_user_api():
    """
    Returns current logged-in user profile from Flask session or SQLite database.
    Clear session if user was logged out / unlinked via WhatsApp.
    """
    if request.args.get("status") == "logged_out":
        session.clear()
        return jsonify({
            "logged_in": False,
            "user": None
        }), 200

    import hashlib

    def resolve_user_picture(email: str, existing_picture: str = "") -> str:
        if existing_picture and len(existing_picture) > 5:
            return existing_picture
        email_clean = email.strip().lower()
        email_hash = hashlib.md5(email_clean.encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=200"

    phone = request.args.get("phone", "")
    if not phone and session.get("user"):
        phone = session.get("user", {}).get("phone", "")

    if phone:
        db_user = db.get_user_credentials(phone)
        if db_user and db_user.get("active_email"):
            email = db_user["active_email"]
            creds_data = db_user.get("creds_data", {})
            existing_pic = creds_data.get("picture", "") if isinstance(creds_data, dict) else ""
            name = (creds_data.get("name") if isinstance(creds_data, dict) else None) or email.split("@")[0]
            picture = resolve_user_picture(email, existing_pic)

            user_data = {
                "name": name,
                "email": email,
                "picture": picture,
                "phone": phone
            }
            session["user"] = user_data
            return jsonify({
                "logged_in": True,
                "user": user_data
            }), 200
        else:
            # User was unlinked/logged out in DB for this phone number! Clear stale browser session
            session.clear()
            return jsonify({
                "logged_in": False,
                "user": None
            }), 200

    user_data = session.get("user")
    if user_data and user_data.get("email"):
        if not user_data.get("picture"):
            user_data["picture"] = resolve_user_picture(user_data["email"], user_data.get("picture", ""))
            session["user"] = user_data

        return jsonify({
            "logged_in": True,
            "user": user_data
        }), 200

    session.clear()
    return jsonify({
        "logged_in": False,
        "user": None
    }), 200


@app.route("/logout", methods=["GET"])
def logout_route():
    """
    Clears Flask session and deletes user credentials from DB, redirecting back to /mailbot.
    """
    phone = request.args.get("phone", "")
    user_data = session.get("user")
    if not phone and user_data and isinstance(user_data, dict):
        phone = user_data.get("phone", "")

    session.clear()

    if phone:
        db.delete_user_credentials(phone)

    return redirect("/mailbot?status=logged_out")

TRAFFIC_INSPECTOR_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Mail Bot AI — Live Traffic Inspector</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a0a0a;
            --card-bg: rgba(255, 255, 255, 0.03);
            --text-heading: #ffffff;
            --text-body: rgba(255, 255, 255, 0.7);
            --border-subtle: rgba(255, 255, 255, 0.08);
            --accent-green: #25D366;
            --accent-blue: #60a5fa;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--bg-dark); color: var(--text-heading); min-height: 100vh; padding: 40px 5%; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
        .title { font-size: 2rem; font-weight: 300; letter-spacing: -0.04em; }
        .badge { background: rgba(37, 211, 102, 0.1); color: var(--accent-green); border: 1px solid rgba(37, 211, 102, 0.2); padding: 6px 16px; border-radius: 999px; font-size: 12px; }
        .btn-link { background: rgba(255,255,255,0.06); color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 999px; border: 1px solid var(--border-subtle); font-size: 13px; }
        .btn-link:hover { background: rgba(255,255,255,0.12); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .card { background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: 20px; padding: 24px; }
        .card-label { font-size: 11px; text-transform: uppercase; color: rgba(255,255,255,0.4); margin-bottom: 8px; }
        .card-val { font-size: 1.5rem; font-weight: 400; color: #fff; }
        .table-container { background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: 20px; overflow: hidden; }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th, td { padding: 16px 24px; border-bottom: 1px solid var(--border-subtle); font-size: 13px; }
        th { background: rgba(255,255,255,0.02); font-weight: 500; color: rgba(255,255,255,0.5); }
        .status-200 { color: #4ade80; }
        .status-304 { color: #60a5fa; }
        .status-302 { color: #f2994a; }
        .status-500 { color: #f87171; }
        .method-tag { background: rgba(255,255,255,0.08); padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 11px; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <span class="badge">LIVE MONITORING</span>
            <h1 class="title" style="margin-top: 10px;">Traffic Inspector Console</h1>
        </div>
        <div style="display: flex; gap: 12px;">
            <a href="/mailbot" class="btn-link">← Back to Mailbot</a>
            <a href="http://localhost:4040" target="_blank" class="btn-link">Open Native ngrok Inspector ↗</a>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-label">Active Tunnel Target</div>
            <div class="card-val" style="font-size: 1rem; word-break: break-all;">{{ ngrok_url }}</div>
        </div>
        <div class="card">
            <div class="card-label">Total Requests Logged</div>
            <div class="card-val">{{ requests|length }}</div>
        </div>
        <div class="card">
            <div class="card-label">Gateway Status</div>
            <div class="card-val" style="color: #4ade80;">100% Operational</div>
        </div>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>METHOD</th>
                    <th>PATH / URI</th>
                    <th>STATUS CODE</th>
                    <th>DURATION</th>
                    <th>TIMESTAMP</th>
                </tr>
            </thead>
            <tbody>
                {% for r in requests %}
                <tr>
                    <td><span class="method-tag">{{ r.request.method if r.request else 'GET' }}</span></td>
                    <td style="font-family: monospace; color: var(--accent-blue);">{{ r.uri }}</td>
                    <td class="status-{{ r.response.status_code if r.response else 200 }}">
                        {{ r.response.status_code if r.response else '200' }} {{ 'OK' if r.response and r.response.status_code == 200 else '' }}
                    </td>
                    <td>{{ (r.duration / 1000000)|round(1) }} ms</td>
                    <td style="color: rgba(255,255,255,0.4);">{{ r.start_time[:19].replace('T', ' ') if r.start_time else 'Just now' }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5" style="text-align: center; color: rgba(255,255,255,0.4); padding: 40px;">No requests recorded yet. Open <a href="/mailbot" style="color:#60a5fa;">/mailbot</a> to generate live traffic!</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

@app.route('/static/uploads/<path:filename>')
def serve_static_uploads(filename):
    uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
    return send_from_directory(uploads_dir, filename)


@app.route("/traffic-inspector", methods=["GET"])
@app.route("/mailbot/traffic-inspector", methods=["GET"])
def traffic_inspector_page():
    req_data = []
    try:
        import urllib.request
        res = urllib.request.urlopen('http://127.0.0.1:4040/api/requests/http', timeout=1)
        data = json.loads(res.read().decode())
        req_data = data.get('requests', [])
    except Exception:
        pass
    return render_template_string(TRAFFIC_INSPECTOR_HTML_TEMPLATE, requests=req_data, ngrok_url=get_base_url())


def process_greenapi_message_sync(chat_id: str, sender_phone: str, incoming_body: str, media_url: str = None, file_name: str = None):
    """
    Synchronous processor for Green API messages that returns the generated response string.
    """
    try:
        print(f"[GreenAPI Sync] Processing message from {chat_id} ({sender_phone}) | Body: '{incoming_body[:60]}...'")
        cmd = incoming_body.upper().strip() if incoming_body else ""
        user_info = db.get_user_credentials(sender_phone)
        pending = db.get_pending_draft(sender_phone)

        # 0. Logout / Unlink Command
        if cmd in ("LOGOUT", "EXIT", "UNLINK", "LOG OUT", "DISCONNECT", "SIGNOUT", "SIGN OUT", "OFF", "STOP", "LEAVE"):
            active_email = user_info.get("active_email") if user_info else None
            if user_info:
                db.delete_user_credentials(sender_phone)
            db.clear_pending_draft(sender_phone)

            if active_email:
                reply_text = (
                    "🚪 *Successfully Logged Out!*\n\n"
                    f"Your Gmail account (`{active_email}`) has been unlinked from phone number `{sender_phone}`.\n\n"
                    "To connect a new Gmail account anytime, reply *NEW*."
                )
            else:
                reply_text = (
                    "ℹ️ *No Active Gmail Account Linked*\n\n"
                    f"Phone number `{sender_phone}` is currently not linked to any Gmail account.\n\n"
                    "To connect a Gmail account, reply *NEW*."
                )
            return reply_text, 200

        # 0b. Help / Manual Command
        if cmd in ("HELP", "MANUAL", "GUIDE", "DOCS", "PDF", "INFO"):
            pdf_manual_url = f"{get_base_url()}/static/uploads/WhatsApp_Mail_Bot_AI_User_Manual.pdf"
            reply_text = (
                "📘 *WhatsApp Mail Bot AI — User Manual & Capabilities*\n\n"
                "Download the visual PDF user manual:\n"
                f"👉 {pdf_manual_url}\n\n"
                "💡 *Quick Commands*:\n"
                "• Reply *1* (or *YES*, *CONFIRM*) to send draft\n"
                "• Reply *LOGOUT* (or *UNLINK*, *EXIT*) to disconnect\n"
                "• Reply *NEW* (or *CONNECT*, *SWITCH*) to link account"
            )
            return reply_text, 200

        effective_brief = construct_effective_brief(incoming_body, media_url, file_name, sender_phone)
        draft = draft_email(effective_brief)

        regex_email, _ = extract_recipient_and_brief(incoming_body)
        target_email = regex_email or (draft.recipient_email if draft.recipient_email else None) or os.getenv("DEFAULT_RECIPIENT_EMAIL", "").strip()

        if not target_email or target_email == "recipient@example.com":
            reply_text = f"🎯 Intent Detected: {draft.detected_intent}. Recipient Email Address Missing."
            return reply_text, 200

        db.save_pending_draft(
            phone_number=sender_phone,
            target_email=target_email,
            subject=draft.subject,
            body=draft.body,
            media_url=media_url,
            file_name=file_name
        )

        intent_label = getattr(draft, 'detected_intent', 'Email Draft')
        recip_display = f"{draft.recipient_name_or_role} (`{target_email}`)" if getattr(draft, 'recipient_name_or_role', None) else f"`{target_email}`"
        sender_email = user_info.get("active_email", "Authorized Gmail") if user_info else "Authorized Gmail"

        reply_text = (
            f"✉️ Email Draft Ready!\n"
            f"🎯 Intent: {intent_label}\n"
            f"👤 Recipient: {recip_display}\n"
            f"📤 Sending From: {sender_email}\n"
            f"📌 Subject: {draft.subject}\n"
            f"• Reply 1 to Send Email"
        )
        return reply_text, 200
    except Exception as err:
        import traceback
        print(f"[GreenAPI Sync Exception]: {traceback.format_exc()}")
        return f"Error: {str(err)}", 500


@app.route("/mailbot", methods=["GET", "POST"])
@app.route("/mailbot/auth", methods=["GET"])
@app.route("/auth", methods=["GET"])
def auth_page():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form or {}
        type_webhook = data.get("typeWebhook")

        # Handle Green API or WhatsApp Webhook POST request directly
        if type_webhook == "incomingMessageReceived" or "messageData" in data or "senderData" in data or "textMessage" in str(data):
            sender_data = data.get("senderData", {})
            chat_id = sender_data.get("chatId", "12345678@c.us")
            sender_phone = sender_data.get("sender", "").replace("@c.us", "")
            if sender_phone and not sender_phone.startswith("+"):
                sender_phone = "+" + sender_phone
            if not sender_phone:
                sender_phone = "+919059130576"

            message_data = data.get("messageData", {})
            type_msg = message_data.get("typeMessage")

            incoming_body = ""
            media_url = None
            file_name = None

            if type_msg in ("textMessage", "extendedTextMessage"):
                text_data = message_data.get("textMessageData") or message_data.get("extendedTextMessageData") or {}
                incoming_body = (text_data.get("textMessage") or text_data.get("text") or "").strip()
            elif type_msg in ("imageMessage", "documentMessage", "fileMessage", "audioMessage", "videoMessage", "stickerMessage"):
                file_data = (
                    message_data.get("fileMessageData") or
                    message_data.get("documentMessageData") or
                    message_data.get("imageMessageData") or
                    message_data.get("videoMessageData") or
                    message_data.get("audioMessageData") or
                    {}
                )
                media_url = file_data.get("downloadUrl") or file_data.get("url") or file_data.get("mediaUrl") or message_data.get("downloadUrl")
                incoming_body = (file_data.get("caption") or file_data.get("title") or "").strip()
                file_name = file_data.get("fileName") or file_data.get("name") or file_data.get("title")
            else:
                text_data = message_data.get("textMessageData") or message_data.get("extendedTextMessageData") or {}
                incoming_body = (
                    text_data.get("textMessage") or
                    text_data.get("text") or
                    data.get("body") or
                    data.get("text") or
                    ""
                ).strip()

            reply_text, status_code = process_greenapi_message_sync(chat_id, sender_phone, incoming_body, media_url, file_name)
            return jsonify({
                "status": "success",
                "message": reply_text,
                "phone": sender_phone,
                "incoming_body": incoming_body
            }), status_code

    phone = request.args.get("phone", "")
    status = request.args.get("status", "")
    email = request.args.get("email", "")
    error = request.args.get("error") or request.args.get("message", "")

    if status == "connected" and email:
        return render_template_string(SUCCESS_HTML_TEMPLATE, email=email, phone=phone or "+919059130576")

    return render_template_string(AUTH_HTML_TEMPLATE, phone=phone, status=status, email=email, error=error)


def check_smtp_credentials(sender_email: str, raw_app_password: str):
    """
    Verifies App Password credentials against Gmail SMTP.
    Strips whitespace from 16-character App Password.
    Tries Port 587 STARTTLS first (standard Gmail SMTP), fallback to Port 465 SSL.
    """
    app_password = raw_app_password.replace(" ", "").strip()
    if not sender_email or not app_password:
        return False, "Email and 16-character App Password are required."

    # Attempt 1: Port 587 STARTTLS
    try:
        print(f"[SMTP Test] Connecting to smtp.gmail.com:587 for '{sender_email}'...")
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=12)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, app_password)
        server.quit()
        print(f"[SMTP Test] SUCCESS on Port 587 for '{sender_email}'!")
        return True, "Authenticated successfully"
    except smtplib.SMTPAuthenticationError as auth_err:
        print(f"[SMTP Test Failed] Port 587 Bad Credentials for '{sender_email}': {auth_err}")
        return False, "Invalid email or App Password. Please ensure 2-Step Verification is active and a 16-character App Password is generated from Google Security."
    except Exception as err1:
        print(f"[SMTP Test] Port 587 connection exception: {err1}. Retrying with Port 465 SSL...")
        # Attempt 2: Port 465 SSL Fallback
        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12)
            server.login(sender_email, app_password)
            server.quit()
            print(f"[SMTP Test] SUCCESS on Port 465 for '{sender_email}'!")
            return True, "Authenticated successfully"
        except smtplib.SMTPAuthenticationError as auth_err:
            print(f"[SMTP Test Failed] Port 465 Bad Credentials for '{sender_email}': {auth_err}")
            return False, "Invalid email or App Password. Please ensure 2-Step Verification is active and a 16-character App Password is generated from Google Security."
        except Exception as err2:
            print(f"[SMTP Test Failed] Port 465 connection exception: {err2}")
            return False, f"SMTP Network Error ({str(err2)}). Alternatively, click 'Sign in with Google Account' below."


@app.route("/api/verify-app-password", methods=["POST"])
def verify_app_password_api():
    """
    Real SMTP Authentication Endpoint with dual-port 587/465 fallback.
    Accepts optional `is_new_user` parameter to support Sign Up registration mode.
    """
    data = request.get_json(silent=True) or request.form or {}
    phone = (data.get("phone") or "").strip()
    sender_email = (data.get("email") or data.get("sender_email") or "").strip()
    raw_app_password = (data.get("app_password") or "").strip()
    app_password = raw_app_password.replace(" ", "")
    is_new_user = bool(data.get("is_new_user", False))

    if not sender_email or not app_password:
        return jsonify({
            "success": False,
            "error": "Email and 16-character App Password are required."
        }), 400

    # Enforce registration check for manual App Password login
    if not is_user_registered(sender_email):
        print(f"[Registration Check Failed] Email '{sender_email}' is not registered yet.")
        return jsonify({
            "success": False,
            "error": "This email is not registered yet. Please click 'Sign up with Google Account' below to register."
        }), 401

    is_valid, msg = check_smtp_credentials(sender_email, raw_app_password)
    if not is_valid:
        return jsonify({
            "success": False,
            "error": msg
        }), 401

    # Save verified credentials securely to SQLite DB (creates/updates profile)
    creds_data = {"sender_email": sender_email, "app_password": app_password, "is_new_user": is_new_user}
    db.save_user_credentials(phone, sender_email, creds_data, auth_type="smtp")

    # Store user profile in Flask session
    session["user"] = {
        "name": sender_email.split("@")[0],
        "email": sender_email,
        "picture": "",
        "phone": phone
    }

    # Check for pending draft & deliver automatically
    pending = db.get_pending_draft(phone)
    if pending:
        try:
            user_info = db.get_user_credentials(phone)
            print(f"Delivering pending draft for '{phone}' via {sender_email}...")
            send_email_with_user_creds(
                user_info=user_info,
                to_email=pending["target_email"],
                subject=pending["subject"],
                body=pending["body"],
                media_url=pending.get("media_url")
            )
            db.clear_pending_draft(phone)
            
            confirm_msg = (
                f"✅ Gmail Authenticated Successfully!\n\n"
                f"Your pending email has been sent to {pending['target_email']}!\n"
                f"📌 Subject: {pending['subject']}\n"
                f"📎 Attachment: {'Yes' if pending.get('media_url') else 'No'}"
            )
            send_twilio_whatsapp_message(phone, confirm_msg)
        except Exception as ex:
            print(f"Error sending pending draft: {ex}")

    return jsonify({
        "success": True,
        "message": "Authenticated successfully",
        "email": sender_email,
        "phone": phone
    }), 200


@app.route("/auth/submit_credentials_success", methods=["GET"])
def submit_credentials_success():
    email = request.args.get("email", "")
    phone = request.args.get("phone", "")
    return render_template_string(SUCCESS_HTML_TEMPLATE, email=email, phone=phone)


@app.route("/auth/submit_credentials", methods=["POST"])
def submit_credentials():
    phone = request.form.get("phone", "").strip()
    sender_email = request.form.get("sender_email", "").strip()
    raw_app_password = request.form.get("app_password", "").strip()
    app_password = raw_app_password.replace(" ", "")

    if not phone or not sender_email or not app_password:
        return "Missing required parameters.", 400

    is_valid, msg = check_smtp_credentials(sender_email, raw_app_password)
    if not is_valid:
        return render_template_string(AUTH_HTML_TEMPLATE, phone=phone, error=msg, email=sender_email)

    import hashlib
    email_clean = sender_email.strip().lower()
    email_hash = hashlib.md5(email_clean.encode('utf-8')).hexdigest()
    picture_url = f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=200"

    creds_data = {
        "sender_email": sender_email,
        "app_password": app_password,
        "name": sender_email.split("@")[0],
        "picture": picture_url
    }
    db.save_user_credentials(phone, sender_email, creds_data, auth_type="smtp")

    session["user"] = {
        "name": sender_email.split("@")[0],
        "email": sender_email,
        "picture": picture_url,
        "phone": phone
    }

    link_msg = (
        "✅ *Gmail Account Successfully Linked!*\n\n"
        f"📱 *Phone Number*: `{phone}`\n"
        f"📧 *Linked Email*: `{sender_email}`\n\n"
        "💡 *Available WhatsApp Commands*:\n"
        "• Send any text brief or document to draft and send emails.\n"
        "• Reply *LOGOUT* (or *UNLINK*, *EXIT*) to disconnect your account directly from WhatsApp.\n"
        "• Reply *NEW* to connect a different Gmail account."
    )

    pending = db.get_pending_draft(phone)
    if pending:
        try:
            user_info = db.get_user_credentials(phone)
            send_email_with_user_creds(
                user_info=user_info,
                to_email=pending["target_email"],
                subject=pending["subject"],
                body=pending["body"],
                media_url=pending.get("media_url"),
                file_name=pending.get("file_name")
            )
            db.clear_pending_draft(phone)
            link_msg += f"\n\n🚀 *Pending Email Delivered* to `{pending['target_email']}`! (Subject: '{pending['subject']}')"
        except Exception as err:
            print(f"Error sending pending draft: {err}")

    try:
        send_whatsapp_notification(phone, link_msg)
    except Exception as ne:
        print("Error sending Form Submit WhatsApp notification:", ne)

    return render_template_string(SUCCESS_HTML_TEMPLATE, email=sender_email, phone=phone)


def send_meta_whatsapp_message(to_phone: str, message_text: str) -> bool:
    """
    Sends an outbound WhatsApp message via Meta official Cloud API REST endpoint.
    Returns True if successful (200 OK), False otherwise.
    """
    access_token = os.getenv("META_ACCESS_TOKEN", "").strip()
    phone_number_id = os.getenv("META_PHONE_NUMBER_ID", "").strip()

    if not access_token or not phone_number_id:
        return False

    clean_phone = to_phone.strip().replace("+", "").replace(" ", "")
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "text",
        "text": {
            "body": message_text
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"[Meta Cloud API Response] ({res.status_code}): {res.text[:100]}")
        return res.status_code == 200
    except Exception as err:
        print(f"[Meta Cloud API Error]: {err}")
        return False


def send_green_api_message(chat_id: str, message_text: str):
    """
    Multi-Gateway Message Dispatcher: Native Local WA Bridge (Port 5001) -> Meta Cloud API -> Green API -> Twilio REST.
    """
    if not chat_id:
        return
    clean_digits = str(chat_id).replace("@c.us", "").replace("@g.us", "").replace("whatsapp:", "").replace("+", "").strip()
    target_chat_id = clean_digits + "@c.us"
    twilio_target = "whatsapp:+" + clean_digits

    # 1. Try Native Local WA Bridge (Port 5001) first for 100% free instant delivery!
    try:
        url = "http://127.0.0.1:5001/send"
        payload = {"to": clean_digits, "message": str(message_text or "")}
        res = requests.post(url, json=payload, timeout=3)
        if res.status_code == 200:
            print(f"[Native WA Bridge] Delivered to {clean_digits} in 0.1s!", flush=True)
            return
    except Exception as err:
        pass

    # 2. Dispatch via Meta Cloud API if configured
    if os.getenv("META_ACCESS_TOKEN", "").strip():
        if send_meta_whatsapp_message(clean_digits, message_text):
            print(f"[Dispatcher] Delivered via Meta Cloud API to {clean_digits}", flush=True)
            return

    # 3. Dispatch via Green API
    id_instance = os.getenv("GREEN_API_ID_INSTANCE", "").strip()
    token_instance = os.getenv("GREEN_API_TOKEN_INSTANCE", "").strip()
    if id_instance and token_instance:
        url = f"https://api.green-api.com/waInstance{id_instance}/sendMessage/{token_instance}"
        payload = {"chatId": target_chat_id, "message": message_text}
        try:
            res = requests.post(url, json=payload, timeout=10)
            print(f"Green API Send Response ({res.status_code}): {res.text[:100]}", flush=True)
            if res.status_code == 200:
                return
        except Exception as err:
            print(f"Green API Send Error: {err}", flush=True)

    # 4. Fallback to Twilio REST notification
    send_twilio_whatsapp_message(twilio_target, message_text)


def construct_effective_brief(incoming_body: str, media_url: str = None, file_name: str = None, sender_phone: str = None) -> str:
    body = (incoming_body or "").strip()
    fname = (file_name or "").strip()

    # Retrieve active draft or cached media for this user
    active_draft = db.get_pending_draft(sender_phone) if sender_phone else None
    cached_media, cached_fname = db.get_recent_media(sender_phone) if sender_phone else (None, None)

    active_media = (active_draft.get("media_url") if active_draft else None) or cached_media or media_url
    active_fname = fname or (active_draft.get("file_name") if active_draft else None) or cached_fname

    if not active_fname and active_media:
        parsed_name = os.path.basename(urllib.parse.urlparse(active_media).path)
        if parsed_name and len(parsed_name) > 3 and not parsed_name.startswith("tmp"):
            active_fname = parsed_name

    # Active Draft Revision Context Handler
    if active_draft and body and any(kw in body.lower() for kw in ("subject", "previous", "update", "change", "revise", "fix", "improve")):
        return (
            f"[Active Pending Email Draft Revision Context]\n"
            f"Attached Document File Title: '{active_fname or 'Document Attachment'}'.\n"
            f"Previous Subject: '{active_draft.get('subject')}'\n"
            f"Target Recipient: '{active_draft.get('target_email')}'\n"
            f"User Revision Request: '{body}'\n\n"
            f"Please update and refine the email draft subject and body based on the user's revision request and the attached document content. NEVER output generic subject lines like 'Updated Submission' or 'Revised Subject Line'. Output a crisp, highly specific subject line incorporating the actual document title."
        )

    if active_fname and body:
        return f"[Attached Document File Title: '{active_fname}'] {body}. Analyze the document file title '{active_fname}' carefully and synthesize a highly specific, professional subject line reflecting the actual document topic/certificate/course (e.g. 'Certificate of Completion: SOLID Principles Every Developer Must Know'). DO NOT use generic fallback subjects like 'Forwarded Document for Your Review'."
    elif active_fname and not body:
        return f"Attached Document File Title: '{active_fname}'. Analyze this document file title, deduce the specific document category, topic, course title, invoice number, or project details, and frame a formal, professional email with a specific, high-impact subject line tailored directly to '{active_fname}'."
    elif body:
        return body
    else:
        return "Please find the attached document forwarded from WhatsApp."


def format_clean_error_message(err: Exception, sender_phone: str) -> str:
    """
    Formats error messages cleanly for WhatsApp.
    If bad credentials (535, Username and Password not accepted, BadCredentials, etc.),
    outputs a friendly message prompting the user to sign in again via our auth link.
    Strips any raw Google URLs to prevent unintended external link previews.
    """
    err_str = str(err)
    if any(k in err_str.lower() for k in ("535", "badcredentials", "username and password not accepted", "authentication failed", "invalid_grant", "smtpauthenticationerror")):
        auth_url = f"{get_base_url()}/mailbot?phone={urllib.parse.quote(sender_phone)}"
        return (
            "⚠️ *Gmail Authentication Failed (Bad Credentials)*\n\n"
            "Your saved Gmail app password or login credentials are invalid or expired.\n\n"
            "Please click the link below to sign in again and reconnect your Gmail account:\n"
            f"👉 {auth_url}"
        )
    
    # Clean up error text by removing any external HTTP/HTTPS URLs to prevent external link previews
    clean_err = re.sub(r'https?://\S+', '', err_str).strip()
    clean_err = re.sub(r'\s+', ' ', clean_err)
    return f"❌ Error sending email: {clean_err}"


_last_processed_msgs = {}

def process_greenapi_message(chat_id: str, sender_phone: str, incoming_body: str, media_url: str, file_name: str = None):
    """
    Processes incoming Green API WhatsApp message, handles commands, generates AI draft, and sends WhatsApp reply.
    """
    msg_key = f"{sender_phone}:{(incoming_body or '').strip()}:{media_url}"
    import time
    now = time.time()
    if msg_key in _last_processed_msgs and (now - _last_processed_msgs[msg_key]) < 5.0:
        print(f"[Deduplicator] Skipping duplicate request for key '{msg_key}' within 5.0s window.")
        return
    _last_processed_msgs[msg_key] = now

    try:
        print(f"[GreenAPI] Processing message from {chat_id} ({sender_phone}) | Body: '{incoming_body[:60]}...' | Media: {bool(media_url)} | File: {file_name}")
        cmd = incoming_body.upper().strip() if incoming_body else ""
        user_info = db.get_user_credentials(sender_phone)
        pending = db.get_pending_draft(sender_phone)

        # 0. Logout / Unlink Command
        if cmd in ("LOGOUT", "EXIT", "UNLINK", "LOG OUT", "DISCONNECT", "SIGNOUT", "SIGN OUT", "OFF", "STOP", "LEAVE"):
            active_email = user_info.get("active_email") if user_info else None
            if user_info:
                db.delete_user_credentials(sender_phone)
            db.clear_pending_draft(sender_phone)

            if active_email:
                reply_text = (
                    "🚪 *Successfully Logged Out!*\n\n"
                    f"Your Gmail account (`{active_email}`) has been unlinked from phone number `{sender_phone}`.\n\n"
                    "To connect a new Gmail account anytime, reply *NEW*."
                )
            else:
                reply_text = (
                    "ℹ️ *No Active Gmail Account Linked*\n\n"
                    f"Phone number `{sender_phone}` is currently not linked to any Gmail account.\n\n"
                    "To connect a Gmail account, reply *NEW*."
                )
            send_green_api_message(chat_id, reply_text)
            return

        # 0b. Help / Manual Command
        if cmd in ("HELP", "MANUAL", "GUIDE", "DOCS", "PDF", "INFO"):
            pdf_manual_url = f"{get_base_url()}/static/uploads/WhatsApp_Mail_Bot_AI_User_Manual.pdf"
            reply_text = (
                "📘 *WhatsApp Mail Bot AI — User Manual & Capabilities*\n\n"
                "Download the visual PDF user manual:\n"
                f"👉 {pdf_manual_url}\n\n"
                "💡 *Quick Commands*:\n"
                "• Reply *1* (or *YES*, *CONFIRM*) to send draft\n"
                "• Reply *LOGOUT* (or *UNLINK*, *EXIT*) to disconnect\n"
                "• Reply *NEW* (or *CONNECT*, *SWITCH*) to link account"
            )
            send_green_api_message(chat_id, reply_text)
            return

        if cmd in ("1", "YES", "CONFIRM", "SEND", "OK", "DISPATCH", "GO") and pending and user_info:
            print(f"Executing confirmed send for '{sender_phone}' via {user_info['active_email']}...")
            try:
                send_email_with_user_creds(
                    user_info=user_info,
                    to_email=pending["target_email"],
                    subject=pending["subject"],
                    body=pending["body"],
                    media_url=pending.get("media_url"),
                    file_name=pending.get("file_name")
                )
                db.clear_pending_draft(sender_phone)
                reply_text = (
                    f"✅ Email sent successfully to {pending['target_email']}!\n\n"
                    f"📌 *Sender*: {user_info['active_email']}\n"
                    f"📌 *Subject*: {pending['subject']}\n"
                    f"📎 *Attachment included*: {'Yes' if pending.get('media_url') else 'No'}"
                )
                send_green_api_message(chat_id, reply_text)
                return
            except Exception as err:
                print(f"[GreenAPI Send Error]: {err}")
                clean_msg = format_clean_error_message(err, sender_phone)
                send_green_api_message(chat_id, clean_msg)
                return

        if cmd in ("NEW", "AUTH", "RESET", "CONNECT", "SWITCH", "LOGIN", "SIGNIN", "SIGN IN"):
            auth_url = f"{get_base_url()}/mailbot?phone={urllib.parse.quote(sender_phone)}"
            reply_text = (
                "🔑 *Connect Another Gmail Account*\n\n"
                "Please click the link below to authorize a new email address:\n"
                f"👉 {auth_url}"
            )
            send_green_api_message(chat_id, reply_text)
            return

        # Debounce & buffer media-only messages to merge with quick follow-up text instructions
        if media_url:
            db.save_recent_media(sender_phone, media_url, file_name)
            if not incoming_body.strip():
                import time
                print(f"[GreenAPI] Media-only message from {sender_phone}. Buffering 3.0s for follow-up text instruction...")
                time.sleep(3.0)
                # Check if follow-up text message already merged this media into a custom draft
                current_draft = db.get_pending_draft(sender_phone)
                if current_draft and "Forwarded Document Attachment" not in current_draft.get("subject", ""):
                    print(f"[GreenAPI] Follow-up text message already merged media into draft '{current_draft['subject']}'. Skipping duplicate response.")
                    return

        effective_brief = construct_effective_brief(incoming_body, media_url, file_name, sender_phone)
        print(f"Drafting email & analyzing recipient from brief: '{effective_brief[:80]}...'")
        draft = draft_email(effective_brief)

        # Recipient Resolution: 1. Regex match -> 2. AI extracted recipient_email -> 3. Default recipient email
        regex_email, _ = extract_recipient_and_brief(incoming_body)
        target_email = regex_email or (draft.recipient_email if draft.recipient_email else None) or os.getenv("DEFAULT_RECIPIENT_EMAIL", "").strip()

        if not target_email or target_email == "recipient@example.com":
            recip_info = f" ({draft.recipient_name_or_role})" if getattr(draft, 'recipient_name_or_role', None) else ""
            reply_text = (
                f"🎯 *Intent Detected*: {draft.detected_intent}\n"
                f"👤 *Recipient Person/Role*{recip_info}: Identified\n\n"
                f"⚠️ *Recipient Email Address Missing*\n"
                f"Please reply with the recipient's email address (e.g. `to: sarah@example.com`) to send this email."
            )
            send_green_api_message(chat_id, reply_text)
            return

        db.save_pending_draft(
            phone_number=sender_phone,
            target_email=target_email,
            subject=draft.subject,
            body=draft.body,
            media_url=media_url,
            file_name=file_name
        )

        # Fetch updated draft to get merged media_url & file_name if auto-merged by db.py
        active_draft = db.get_pending_draft(sender_phone)
        effective_media_url = (active_draft.get("media_url") if active_draft else None) or media_url
        effective_fname = (active_draft.get("file_name") if active_draft else None) or file_name

        attachment_display = "No"
        if effective_media_url:
            attachment_display = f"Yes ({effective_fname})" if effective_fname else "Yes"

        intent_label = getattr(draft, 'detected_intent', 'Email Draft')
        recip_display = f"{draft.recipient_name_or_role} (`{target_email}`)" if getattr(draft, 'recipient_name_or_role', None) else f"`{target_email}`"
        sender_email = user_info.get("active_email", "Authorized Gmail") if user_info else "Authorized Gmail"

        pdf_manual_url = f"{get_base_url()}/static/uploads/WhatsApp_Mail_Bot_AI_User_Manual.pdf"
        manual_footer = f"\n\n📘 *User Manual & Capabilities*: {pdf_manual_url}"

        if user_info:
            reply_text = (
                f"✉️ *Email Draft Ready!*\n"
                f"🎯 *Intent*: {intent_label}\n"
                f"👤 *Recipient*: {recip_display}\n"
                f"📤 *Sending From*: `{sender_email}`\n"
                f"📌 *Subject*: {draft.subject}\n"
                f"📎 *Attachment*: {attachment_display}\n\n"
                f"• Reply *1* to Send Email\n"
                f"• Reply *NEW* to Connect Another Account"
                f"{manual_footer}"
            )
        else:
            auth_url = f"{get_base_url()}/mailbot?phone={urllib.parse.quote(sender_phone)}"
            reply_text = (
                f"✉️ *Email Draft Ready!*\n"
                f"🎯 *Intent*: {intent_label}\n"
                f"👤 *Recipient*: {recip_display}\n"
                f"📤 *Sending From*: `{sender_email}`\n"
                f"📌 *Subject*: {draft.subject}\n"
                f"📎 *Attachment*: {attachment_display}\n\n"
                f"🔑 *Gmail Authentication Required*\n"
                f"Please click below to connect your Gmail account:\n"
                f"👉 {auth_url}\n\n"
                f"*(Once authorized, your email will be sent automatically!)*"
                f"{manual_footer}"
            )

        print(f"Sending Green API reply to {chat_id}...")
        send_green_api_message(chat_id, reply_text)

    except Exception as err:
        import traceback
        print(f"[GreenAPI Exception]: {traceback.format_exc()}")
        try:
            clean_msg = format_clean_error_message(err, sender_phone)
            send_green_api_message(chat_id, clean_msg)
        except Exception:
            pass


@app.route("/greenapi", methods=["GET", "POST"])
@app.route("/greenapi/", methods=["GET", "POST"])
def greenapi_webhook():
    data = request.get_json(silent=True) or {}
    
    # Unified Webhook Router: If payload contains Meta's 'entry' array, delegate to meta_whatsapp_webhook
    if "entry" in data or request.args.get("hub.mode") == "subscribe":
        return meta_whatsapp_webhook()

    type_webhook = data.get("typeWebhook")
    print(f"[GreenAPI Webhook Received] typeWebhook={type_webhook} | keys={list(data.keys())}", flush=True)

    if not type_webhook or type_webhook in ("incomingMessageReceived", "incomingMessage"):
        sender_data = data.get("senderData", {})
        chat_id = sender_data.get("chatId") or sender_data.get("sender") or data.get("chatId") or ""
        raw_sender = sender_data.get("sender") or sender_data.get("chatId") or data.get("sender") or ""
        sender_phone = db.clean_phone_number(raw_sender.replace("@c.us", "").replace("@g.us", ""))

        message_data = data.get("messageData", {})
        type_msg = message_data.get("typeMessage")

        incoming_body = ""
        media_url = None
        file_name = None

        if type_msg in ("textMessage", "extendedTextMessage"):
            text_data = message_data.get("textMessageData") or message_data.get("extendedTextMessageData") or {}
            incoming_body = (text_data.get("textMessage") or text_data.get("text") or "").strip()
        elif type_msg in ("imageMessage", "documentMessage", "fileMessage", "audioMessage", "videoMessage", "stickerMessage"):
            file_data = (
                message_data.get("fileMessageData") or
                message_data.get("documentMessageData") or
                message_data.get("imageMessageData") or
                message_data.get("videoMessageData") or
                message_data.get("audioMessageData") or
                {}
            )
            media_url = file_data.get("downloadUrl") or file_data.get("url") or file_data.get("mediaUrl") or message_data.get("downloadUrl")
            incoming_body = (file_data.get("caption") or file_data.get("title") or "").strip()
            file_name = file_data.get("fileName") or file_data.get("name") or file_data.get("title")
        else:
            text_data = message_data.get("textMessageData") or message_data.get("extendedTextMessageData") or {}
            incoming_body = (
                text_data.get("textMessage") or
                text_data.get("text") or
                data.get("body") or
                data.get("text") or
                ""
            ).strip()

        if sender_phone:
            # Run process_greenapi_message asynchronously in a background worker thread
            import threading
            threading.Thread(
                target=process_greenapi_message,
                args=(chat_id, sender_phone, incoming_body, media_url, file_name)
            ).start()

    return Response("OK", status=200)


@app.route("/meta", methods=["GET", "POST"])
@app.route("/webhook", methods=["GET", "POST"])
def meta_whatsapp_webhook():
    """
    Official Meta WhatsApp Cloud API Webhook Handler.
    GET: Handles Meta Webhook Verification challenge.
    POST: Processes incoming Meta WhatsApp messages and triggers process_greenapi_message.
    """
    # 1. Meta Webhook Verification GET Handler
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        verify_token = os.getenv("META_VERIFY_TOKEN", "whatsapp_mail_bot_secret_token")

        if mode == "subscribe" and token == verify_token:
            print("[Meta Cloud API] Webhook verified successfully!")
            return Response(challenge, status=200, mimetype="text/plain")
        else:
            print(f"[Meta Cloud API] Verification failed! Expected token '{verify_token}', got '{token}'")
            return Response("Forbidden", status=403)

    # 2. Meta Webhook Incoming Message POST Handler
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        print(f"[Meta Webhook POST Received] keys={list(data.keys())}", flush=True)

        try:
            entries = data.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    contacts = value.get("contacts", [])

                    for msg in messages:
                        from_number = msg.get("from", "")
                        sender_phone = db.clean_phone_number(from_number)
                        chat_id = sender_phone.replace("+", "") + "@c.us"
                        msg_type = msg.get("type", "text")

                        incoming_body = ""
                        media_url = None
                        file_name = None

                        if msg_type == "text":
                            incoming_body = msg.get("text", {}).get("body", "").strip()
                        elif msg_type in ("image", "document", "audio", "video"):
                            media_obj = msg.get(msg_type, {})
                            incoming_body = media_obj.get("caption", "").strip()
                            file_name = media_obj.get("filename") or media_obj.get("title")

                        if sender_phone:
                            print(f"[Meta Webhook] Processing message from {sender_phone}: '{incoming_body[:40]}...'", flush=True)
                            import threading
                            threading.Thread(
                                target=process_greenapi_message,
                                args=(chat_id, sender_phone, incoming_body, media_url, file_name)
                            ).start()
        except Exception as err:
            import traceback
            print(f"[Meta Webhook Exception]: {traceback.format_exc()}", flush=True)

        return Response("EVENT_RECEIVED", status=200)


@app.route("/whatsapp", methods=["POST"])
@app.route("/whats", methods=["POST"])
@app.route("/whatsapp/", methods=["POST"])
def whatsapp_webhook():
    sender_phone = request.values.get("From", "").strip()
    incoming_body = request.values.get("Body", "").strip()
    num_media = int(request.values.get("NumMedia", "0"))
    media_url = request.values.get("MediaUrl0") if num_media > 0 else None
    file_name = request.values.get("Filename0")

    clean_phone = db.clean_phone_number(sender_phone)
    print(f"[Twilio Webhook Received] From: {clean_phone} | Body: '{incoming_body[:40]}...'", flush=True)

    resp = MessagingResponse()

    if not incoming_body and not media_url:
        resp.message("⚠️ Please provide an email brief text or attach a file.")
        return Response(str(resp), mimetype="application/xml")

    cmd = incoming_body.upper().strip() if incoming_body else ""

    # Handshake / Join Sandbox Command
    if cmd.startswith("JOIN"):
        resp.message(
            "🎉 *Connected to WhatsApp Mail Bot AI!*\n\n"
            "You are all set! You can now send any email brief or attach documents (PDF/Images) to draft and send emails instantly.\n\n"
            "💡 *Try sending*:\n"
            "• 'Send email to recipient@example.com regarding project update'\n"
            "• Attach a PDF file to draft a document email"
        )
        return Response(str(resp), mimetype="application/xml")

    user_info = db.get_user_credentials(clean_phone)
    pending = db.get_pending_draft(clean_phone)

    # 0. Logout / Unlink Command
    if cmd in ("LOGOUT", "EXIT", "UNLINK", "LOG OUT", "DISCONNECT", "SIGNOUT", "SIGN OUT", "OFF", "STOP", "LEAVE"):
        active_email = user_info.get("active_email") if user_info else None
        if user_info:
            db.delete_user_credentials(clean_phone)
        db.clear_pending_draft(clean_phone)

        if active_email:
            reply_text = (
                "🚪 *Successfully Logged Out!*\n\n"
                f"Your Gmail account (`{active_email}`) has been unlinked from phone number `{clean_phone}`.\n\n"
                "To connect a new Gmail account anytime, reply *NEW*."
            )
        else:
            reply_text = (
                "ℹ️ *No Active Gmail Account Linked*\n\n"
                f"Phone number `{clean_phone}` is currently not linked to any Gmail account.\n\n"
                "To connect a Gmail account, reply *NEW*."
            )
        resp.message(reply_text.replace("&", "and"))
        return Response(str(resp), mimetype="application/xml")

    # 0b. Help / Manual Command
    if cmd in ("HELP", "MANUAL", "GUIDE", "DOCS", "PDF", "INFO"):
        pdf_manual_url = f"{get_base_url()}/static/uploads/WhatsApp_Mail_Bot_AI_User_Manual.pdf"
        reply_text = (
            "📘 *WhatsApp Mail Bot AI — User Manual and Capabilities*\n\n"
            "Download the visual PDF user manual:\n"
            f"👉 {pdf_manual_url}\n\n"
            "💡 *Quick Commands*:\n"
            "• Reply *1* (or *YES*, *CONFIRM*) to send draft\n"
            "• Reply *LOGOUT* (or *UNLINK*, *EXIT*) to disconnect\n"
            "• Reply *NEW* (or *CONNECT*, *SWITCH*) to link account"
        )
        resp.message(reply_text.replace("&", "and"))
        return Response(str(resp), mimetype="application/xml")

    # 1. Quick action command: "1", "YES", "CONFIRM"
    if cmd in ("1", "YES", "CONFIRM", "SEND", "OK", "DISPATCH", "GO") and pending and user_info:
        try:
            print(f"Executing confirmed send for '{clean_phone}' via {user_info['active_email']}...")
            send_email_with_user_creds(
                user_info=user_info,
                to_email=pending["target_email"],
                subject=pending["subject"],
                body=pending["body"],
                media_url=pending.get("media_url"),
                file_name=pending.get("file_name")
            )
            db.clear_pending_draft(clean_phone)
            reply_text = (
                f"✅ Email sent successfully to {pending['target_email']}!\n\n"
                f"📌 *Sender*: {user_info['active_email']}\n"
                f"📌 *Subject*: {pending['subject']}\n"
                f"📎 *Attachment included*: {'Yes' if pending.get('media_url') else 'No'}"
            )
            resp.message(reply_text.replace("&", "and"))
            return Response(str(resp), mimetype="application/xml")
        except Exception as err:
            print(f"[Twilio Send Error]: {err}")
            clean_msg = format_clean_error_message(err, clean_phone)
            resp.message(clean_msg.replace("&", "and"))
            return Response(str(resp), mimetype="application/xml")

    # 2. Command: "NEW", "AUTH", "RESET"
    if cmd in ("NEW", "AUTH", "RESET", "CONNECT", "SWITCH", "LOGIN", "SIGNIN", "SIGN IN"):
        auth_url = f"{get_base_url()}/mailbot?phone={urllib.parse.quote(clean_phone)}"
        reply_text = (
            "🔑 *Connect Another Gmail Account*\n\n"
            "Please click the link below to authorize a new email address:\n"
            f"👉 {auth_url}"
        )
        resp.message(reply_text.replace("&", "and"))
        return Response(str(resp), mimetype="application/xml")

    try:
        # Debounce & buffer media-only messages
        if media_url:
            db.save_recent_media(clean_phone, media_url, file_name)
            if not incoming_body.strip():
                import time
                print(f"[Twilio] Media-only message from {clean_phone}. Buffering 3.0s...")
                time.sleep(3.0)
                current_draft = db.get_pending_draft(clean_phone)
                if current_draft and "Forwarded Document Attachment" not in current_draft.get("subject", ""):
                    resp.message(f"📎 Attached media file linked to your email draft for '{current_draft['target_email']}'.")
                    return Response(str(resp), mimetype="application/xml")

        effective_brief = construct_effective_brief(incoming_body, media_url, file_name, clean_phone)
        print(f"Drafting email & analyzing recipient from brief for '{clean_phone}': '{effective_brief[:80]}...'")
        draft = draft_email(effective_brief)

        # Recipient Resolution
        regex_email, _ = extract_recipient_and_brief(incoming_body)
        target_email = regex_email or (draft.recipient_email if draft.recipient_email else None) or os.getenv("DEFAULT_RECIPIENT_EMAIL", "").strip()

        if not target_email or target_email == "recipient@example.com":
            recip_info = f" ({draft.recipient_name_or_role})" if getattr(draft, 'recipient_name_or_role', None) else ""
            reply_text = (
                f"🎯 *Intent Detected*: {draft.detected_intent}\n"
                f"👤 *Recipient Person/Role*{recip_info}: Identified\n\n"
                f"⚠️ *Recipient Email Address Missing*\n"
                f"Please reply with the recipient's email address (e.g. `to: sarah@example.com`) to send this email."
            )
            resp.message(reply_text.replace("&", "and"))
            return Response(str(resp), mimetype="application/xml")

        # Step B: Save pending draft
        db.save_pending_draft(
            phone_number=clean_phone,
            target_email=target_email,
            subject=draft.subject,
            body=draft.body,
            media_url=media_url,
            file_name=file_name
        )

        active_draft = db.get_pending_draft(clean_phone)
        effective_media_url = active_draft.get("media_url") if active_draft else media_url

        # Step C: Format reply message
        intent_label = getattr(draft, 'detected_intent', 'Email Draft')
        recip_display = f"{draft.recipient_name_or_role} (`{target_email}`)" if getattr(draft, 'recipient_name_or_role', None) else f"`{target_email}`"

        pdf_manual_url = f"{get_base_url()}/static/uploads/WhatsApp_Mail_Bot_AI_User_Manual.pdf"
        manual_footer = f"\n\n📘 *User Manual and Capabilities*: {pdf_manual_url}"

        if user_info:
            reply_text = (
                f"✉️ *Email Draft Ready!*\n"
                f"🎯 *Intent*: {intent_label}\n"
                f"👤 *Recipient*: {recip_display}\n\n"
                f"📌 *Subject*: {draft.subject}\n"
                f"📎 *Attachment*: {'Yes' if effective_media_url else 'No'}\n\n"
                f"Send from saved email `{user_info['active_email']}`?\n"
                f"• Reply *1* to Send Email\n"
                f"• Reply *NEW* to Connect Another Account"
                f"{manual_footer}"
            )
        else:
            auth_url = f"{get_base_url()}/mailbot?phone={urllib.parse.quote(clean_phone)}"
            reply_text = (
                f"✉️ *Email Draft Ready!*\n"
                f"🎯 *Intent*: {intent_label}\n"
                f"👤 *Recipient*: {recip_display}\n\n"
                f"📌 *Subject*: {draft.subject}\n"
                f"📎 *Attachment*: {'Yes' if effective_media_url else 'No'}\n\n"
                f"🔑 *Gmail Authentication Required*\n"
                f"Please click below to connect your Gmail account:\n"
                f"👉 {auth_url}\n\n"
                f"*(Once authorized, your email will be sent automatically!)*"
                f"{manual_footer}"
            )

        resp.message(reply_text.replace("&", "and"))
        return Response(str(resp).encode('utf-8'), mimetype="application/xml; charset=utf-8")

    except Exception as err:
        print(f"[Twilio Exception]: {err}")
        clean_msg = format_clean_error_message(err, clean_phone)
        resp.message(clean_msg.replace("&", "and"))
        return Response(str(resp).encode('utf-8'), mimetype="application/xml; charset=utf-8")


def start_greenapi_notification_poller():
    """
    Background worker thread that polls Green API receiveNotification API every 2 seconds.
    Guarantees instant message processing even if Green API console webhooks are not configured!
    """
    import time
    def poll_worker():
        print("[GreenAPI Poller] Background polling thread active.")
        while True:
            try:
                id_instance = os.getenv("GREEN_API_ID_INSTANCE", "").strip()
                token_instance = os.getenv("GREEN_API_TOKEN_INSTANCE", "").strip()
                if not id_instance or not token_instance:
                    time.sleep(5)
                    continue

                url = f"https://api.green-api.com/waInstance{id_instance}/receiveNotification/{token_instance}"
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if data and isinstance(data, dict) and data.get("receiptId"):
                        receipt_id = data.get("receiptId")
                        body_data = data.get("body", {})
                        type_webhook = body_data.get("typeWebhook")

                        if not type_webhook or type_webhook in ("incomingMessageReceived", "incomingMessage"):
                            sender_data = body_data.get("senderData", {})
                            chat_id = sender_data.get("chatId") or sender_data.get("sender") or body_data.get("chatId") or ""
                            raw_sender = sender_data.get("sender") or sender_data.get("chatId") or body_data.get("sender") or ""
                            sender_phone = db.clean_phone_number(raw_sender.replace("@c.us", "").replace("@g.us", ""))

                            message_data = body_data.get("messageData", {})
                            type_msg = message_data.get("typeMessage")

                            incoming_body = ""
                            media_url = None
                            file_name = None

                            if type_msg in ("textMessage", "extendedTextMessage"):
                                text_data = message_data.get("textMessageData") or message_data.get("extendedTextMessageData") or {}
                                incoming_body = (text_data.get("textMessage") or text_data.get("text") or "").strip()
                            elif type_msg in ("imageMessage", "documentMessage", "fileMessage", "audioMessage", "videoMessage", "stickerMessage"):
                                file_data = (
                                    message_data.get("fileMessageData") or
                                    message_data.get("documentMessageData") or
                                    message_data.get("imageMessageData") or
                                    message_data.get("videoMessageData") or
                                    message_data.get("audioMessageData") or
                                    {}
                                )
                                media_url = file_data.get("downloadUrl") or file_data.get("url") or file_data.get("mediaUrl") or message_data.get("downloadUrl")
                                incoming_body = (file_data.get("caption") or file_data.get("title") or "").strip()
                                file_name = file_data.get("fileName") or file_data.get("name") or file_data.get("title")
                            else:
                                text_data = message_data.get("textMessageData") or message_data.get("extendedTextMessageData") or {}
                                incoming_body = (
                                    text_data.get("textMessage") or
                                    text_data.get("text") or
                                    body_data.get("body") or
                                    body_data.get("text") or
                                    ""
                                ).strip()

                            if sender_phone:
                                print(f"[GreenAPI Poller] Fetched message from {sender_phone}: '{incoming_body[:40]}...'")
                                process_greenapi_message(chat_id, sender_phone, incoming_body, media_url, file_name)

                        # Delete notification from Green API queue after processing
                        del_url = f"https://api.green-api.com/waInstance{id_instance}/deleteNotification/{token_instance}/{receipt_id}"
                        requests.delete(del_url, timeout=5)
            except Exception as err:
                pass
            time.sleep(2)

    import threading
    t = threading.Thread(target=poll_worker, daemon=True)
    t.start()

# Launch background Green API poller daemon
start_greenapi_notification_poller()


PRIVACY_POLICY_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy — WhatsApp Mail Bot AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #0f172a; color: #f8fafc; padding: 40px 20px; line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; background: #1e293b; padding: 40px; border-radius: 16px; border: 1px solid #334155; }
        h1 { color: #38bdf8; }
        h2 { color: #f1f5f9; margin-top: 24px; }
        p { color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Privacy Policy</h1>
        <p>Last updated: August 17, 2026</p>
        <h2>1. Information We Collect</h2>
        <p>WhatsApp Mail Bot AI processes incoming WhatsApp messages and attached documents strictly to compose and send user-authorized emails via Gmail OAuth API.</p>
        <h2>2. Data Security & Storage</h2>
        <p>Your authentication tokens are stored securely in isolated SQLite databases. We never share or sell user data to third parties.</p>
        <h2>3. Third-Party Services</h2>
        <p>We integrate with Google OAuth API and Meta WhatsApp Cloud API to provide automated messaging services.</p>
        <h2>4. Contact Us</h2>
        <p>If you have any questions, contact us at saakethkazipeta@gmail.com.</p>
    </div>
</body>
</html>
"""

@app.route("/privacy")
@app.route("/privacy_policy")
def privacy_policy():
    return render_template_string(PRIVACY_POLICY_HTML)


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    print(f"Starting Multi-User WhatsApp-to-Email Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=debug)

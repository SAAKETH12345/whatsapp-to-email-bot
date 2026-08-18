@echo off
title WhatsApp AI Mail Bot (Native 0-Limit Engine)
echo ===================================================
echo 🚀 Starting Native WhatsApp Web Bot (0 Limits)
echo ===================================================
echo 1. Launching Native WhatsApp Bridge on Port 5001...
start "WhatsApp Native Bridge" node bridge.js
echo 2. Launching Flask Server on Port 5000...
python app.py

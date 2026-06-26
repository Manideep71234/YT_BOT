import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import urllib.parse
import subprocess
import base64
import zipfile
import shutil

def send_email_notification(subject, body):
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    recipient = os.getenv("EMAIL_RECIPIENT")

    if not sender or not password or not recipient:
        print("Email configuration is missing. Cannot send notification.")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        text = msg.as_string()
        server.sendmail(sender, recipient, text)
        server.quit()
        print(f"Email notification sent to {recipient}")
        return True
    except Exception as e:
        print(f"Failed to send email notification: {e}")
        return False

def send_whatsapp_message(text):
    phone_number = os.getenv("WHATSAPP_PHONE_NUMBER")
    
    if not phone_number:
        print("WHATSAPP_PHONE_NUMBER is missing. Cannot send notification.")
        return False

    phone_number = phone_number.replace("+", "")
    
    # Use the wwebjs local session script
    wa_dir = os.path.join("scripts", "whatsapp")
    wa_session_b64 = os.getenv("WA_SESSION_B64")
    auth_dir = os.path.join(wa_dir, "wwebjs_auth")
    zip_path = os.path.join(wa_dir, "wwebjs_auth.zip")
    
    # Extract session token from B64 if provided and auth doesn't exist
    if wa_session_b64 and not os.path.exists(auth_dir):
        print("[whatsapp] Decoding WA_SESSION_B64 token...")
        zip_bytes = base64.b64decode(wa_session_b64)
        with open(zip_path, 'wb') as f:
            f.write(zip_bytes)
    
    # Extract the zip file if it exists (handles both B64 and GitHub repo downloads)
    if os.path.exists(zip_path) and not os.path.exists(auth_dir):
        print("[whatsapp] Extracting session from local zip...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(wa_dir)
            os.remove(zip_path)
            print("[whatsapp] Successfully extracted session token.")
        except Exception as e:
            print(f"[whatsapp] Failed to extract session token: {e}")

    # Ensure dependencies are installed
    if not os.path.exists(os.path.join(wa_dir, "node_modules")):
        print("[whatsapp] Installing node deps...")
        subprocess.run(["npm", "install", "--prefix", wa_dir], capture_output=True, check=True)

    try:
        result = subprocess.run(
            ["node", "send.js", text, phone_number],
            cwd=wa_dir, capture_output=True, text=True, encoding="utf-8", timeout=90
        )
        if result.returncode == 0:
            print("WhatsApp notification sent successfully via wwebjs!")
            return True
        else:
            print(f"Failed to send WhatsApp message. Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error executing WhatsApp send.js: {e}")
        return False

def send_telegram_message(text):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram configuration is missing. Cannot send notification.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Telegram notification sent successfully!")
            return True
        else:
            print(f"Failed to send Telegram message. Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

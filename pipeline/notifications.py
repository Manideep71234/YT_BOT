import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import urllib.parse

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
    api_key = os.getenv("WHATSAPP_API_KEY")

    if not phone_number or not api_key or phone_number == "+1234567890":
        print("WhatsApp configuration is missing. Cannot send notification.")
        return False

    phone_number = phone_number.replace("+", "")
    encoded_text = urllib.parse.quote(text)
    
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone_number}&text={encoded_text}&apikey={api_key}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("WhatsApp notification sent successfully!")
            return True
        else:
            print(f"Failed to send WhatsApp message. Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
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

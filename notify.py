import os, smtplib, ssl, requests
from email.message import EmailMessage

def notify_telegram(text: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
        return True
    except Exception:
        return False

def notify_email(subject: str, body: str):
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    pwd  = os.getenv("SMTP_PASS", "").strip()
    sender = os.getenv("EMAIL_FROM", "").strip()
    recipient = os.getenv("EMAIL_TO", "").strip()

    if not all([host, port, user, pwd, sender, recipient]):
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=ctx)
        server.login(user, pwd)
        server.send_message(msg)
    return True

def push_alert(title: str, body: str):
    ok_tg = notify_telegram(f"{title}\n\n{body}")
    ok_em = notify_email(title, body)
    return ok_tg or ok_em

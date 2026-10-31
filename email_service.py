import os
import smtplib
import asyncio
from email.message import EmailMessage
import mimetypes
from pathlib import Path
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, DEFAULT_EMAIL_TO

def _send_email_sync(to_email: str, subject: str, html_content: str, attachment_paths: list[str] = None) -> tuple[bool, str]:
    target_to = to_email.strip() if to_email else DEFAULT_EMAIL_TO.strip()
    if not target_to:
        return False, "No recipient email provided and DEFAULT_EMAIL_TO is empty in .env"
    
    if not SMTP_USER or not SMTP_PASS:
        return False, "SMTP credentials (SMTP_USER, SMTP_PASS) not configured in .env"

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = target_to

    # Body
    msg.set_content("Please enable HTML viewing to read this agent report.")
    msg.add_alternative(html_content, subtype='html')

    # Attachments
    if attachment_paths:
        for file_path in attachment_paths:
            path = Path(file_path)
            if not path.is_file():
                continue
            ctype, encoding = mimetypes.guess_type(str(path))
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)

            with open(path, 'rb') as f:
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=path.name
                )

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        return True, f"Email sent to {target_to}"
    except Exception as e:
        return False, f"SMTP Error: {str(e)}"

async def send_email_async(to_email: str, subject: str, html_content: str, attachment_paths: list[str] = None) -> tuple[bool, str]:
    """Sends an email in a non-blocking thread."""
    return await asyncio.to_thread(_send_email_sync, to_email, subject, html_content, attachment_paths)

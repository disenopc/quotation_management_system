import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from config import Config
from models import Client, Inquiry
from datetime import datetime
import re
import threading
import time
import logging

# Configurar logging profesional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("email_handler.log"),
        logging.StreamHandler()
    ]
)

class EmailHandler:
    """
    Handle email operations: fetch inquiries and send responses.
    Supports Gmail, Outlook, and other IMAP/SMTP providers.
    Can run a professional monitoring loop in a separate thread.
    """
    
    def __init__(self):
        self.imap_server = Config.IMAP_SERVER
        self.imap_port = Config.IMAP_PORT
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.email_address = Config.EMAIL_ADDRESS
        self.email_password = Config.EMAIL_PASSWORD
        self._monitoring_thread = None
        self._stop_event = threading.Event()
    
    def connect_imap(self):
        """Connect to IMAP server"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            return mail
        except Exception as e:
            logging.error(f"IMAP connection failed: {str(e)}")
            raise
    
    def connect_smtp(self):
        """Connect to SMTP server"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.email_password)
            return server
        except Exception as e:
            logging.error(f"SMTP connection failed: {str(e)}")
            raise

    # --- Métodos de utilidad ---
    def decode_email_header(self, header):
        decoded, charset = decode_header(header)[0]
        if charset:
            decoded = decoded.decode(charset)
        return decoded

    def extract_email_address(self, from_header):
        match = re.search(r'<(.+?)>', from_header)
        return match.group(1) if match else from_header

    def extract_name_from_email(self, from_header):
        match = re.match(r'(.*)<', from_header)
        return match.group(1).strip() if match else None

    def get_email_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
        else:
            return msg.get_payload(decode=True).decode()
        return ""

    def fetch_new_emails(self):
        """
        Fetch unread emails and return a list of dicts with keys: from, subject, body
        """
        new_emails = []
        try:
            mail = self.connect_imap()
            mail.select("inbox")
            status, messages = mail.search(None, '(UNSEEN)')
            if status != "OK":
                logging.warning("No new messages found")
                return new_emails
            for num in messages[0].split():
                status, data = mail.fetch(num, '(RFC822)')
                if status != "OK":
                    continue
                msg = email.message_from_bytes(data[0][1])
                from_header = self.decode_email_header(msg["From"])
                subject = self.decode_email_header(msg["Subject"])
                body = self.get_email_body(msg)
                new_emails.append({
                    "from": self.extract_email_address(from_header),
                    "name": self.extract_name_from_email(from_header),
                    "subject": subject,
                    "body": body
                })
            mail.logout()
        except Exception as e:
            logging.error(f"Error fetching emails: {str(e)}")
        return new_emails
  

    def send_email(self, to_address, subject, body):
        """Send a single email"""
        try:
            server = self.connect_smtp()
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = to_address
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            server.sendmail(self.email_address, to_address, msg.as_string())
            server.quit()
            logging.info(f"Email sent to {to_address} with subject '{subject}'")
        except Exception as e:
            logging.error(f"Failed to send email: {str(e)}")

    def send_bulk_emails(self, recipients, subject, body):
        """Send emails in bulk"""
        for r in recipients:
            self.send_email(r, subject, body)

    def test_connection(self):
        """Test IMAP and SMTP connections"""
        try:
            self.connect_imap().logout()
            self.connect_smtp().quit()
            logging.info("IMAP and SMTP connections successful")
            return True
        except Exception as e:
            logging.error(f"Connection test failed: {str(e)}")
            return False

    # --- Monitoreo profesional en thread ---
    def start_email_monitoring(self, interval=60):
        """
        Start email monitoring in a separate daemon thread.
        interval: seconds between checks
        """
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logging.warning("Email monitoring already running")
            return
        
        logging.info(f"Starting email monitoring every {interval} seconds...")
        self._stop_event.clear()
        self._monitoring_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()

    def _monitor_loop(self, interval):
        """Loop that fetches new emails periodically"""
        while not self._stop_event.is_set():
            try:
                new_emails = self.fetch_new_emails()
                for email_data in new_emails:
                    logging.info(f"New inquiry from {email_data['from']}: {email_data['subject']}")
                    # Aquí podrías integrar tu AI Assistant para generar respuesta automáticamente
                    # response_text = ai_assistant.generate_response(email_data['subject'], email_data['body'])
                    # self.send_email(email_data['from'], "Re: " + email_data['subject'], response_text)
            except Exception as e:
                logging.error(f"Error during email monitoring: {str(e)}")
            time.sleep(interval)
    
    def stop_email_monitoring(self):
        """Stop the monitoring thread gracefully"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logging.info("Stopping email monitoring...")
            self._stop_event.set()
            self._monitoring_thread.join()
            logging.info("Email monitoring stopped.")
        else:
            logging.info("No monitoring thread to stop.")

# Crear instancia global que puede ser importada
email_handler = EmailHandler()
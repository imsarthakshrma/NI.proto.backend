from email.mime.base import MIMEBase
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pydantic import Field
from datetime import datetime  
import logging

from langchain_core.tools import BaseTool, tool

logger = logging.getLogger(__name__)

@dataclass
class EmailDetails:
    recipient: str
    subject: str
    body: str
    sender: str = ""
    cc: List[str] = None
    bcc: List[str] = None
    attachments: List[str] = None
    html_body: str = ""
    on_behalf_of: str = ""  


class SendEmailTool(BaseTool):
    recipient: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body content")
    cc: Optional[List[str]] = Field(description="CC email addresses", default=None)
    bcc: Optional[List[str]] = Field(description="BCC email addresses", default=None)
    html_body: Optional[str] = Field(description="HTML email body (optional)", default="")
    attachments: Optional[List[str]] = Field(description="Attachments (optional)", default=None)
    sender: Optional[str] = Field(description="Sender (optional)", default="")
    on_behalf_of: Optional[str] = Field(description="Native IQ on behalf of (username)", default="")


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('SMTP_EMAIL')
        self.sender_password = os.getenv('SMTP_PASSWORD')
        self.sender_name = os.getenv('SMTP_SENDER_NAME', 'Native IQ')
    
    def send_email(self, email: EmailDetails) -> Dict[str, Any]:
        try:
            if not self.sender_email or not self.sender_password:
                return {
                    "success": False,
                    "error": "Email credentials not configured"
                }
            
            # Create message
            msg = MIMEMultipart('alternative')
            
            # Handle on_behalf_of in From header
            if email.on_behalf_of:
                from_header = f"{self.sender_name} on behalf of {email.on_behalf_of} <{self.sender_email}>"
            else:
                from_header = f"{self.sender_name} <{self.sender_email}>"
            
            msg['From'] = from_header
            msg['To'] = email.recipient
            msg['Subject'] = email.subject

            if email.cc:
                msg['Cc'] = ', '.join(email.cc)
            if email.bcc:
                msg['Bcc'] = ', '.join(email.bcc)
            
            # signature to body if on_behalf_of is provided
            body_content = email.body
            if email.on_behalf_of:
                signature = f"\n\n{email.on_behalf_of}\n\nNative IQ on behalf of {email.on_behalf_of}"
                body_content = f"{email.body}{signature}"
            
            # Add body
            if email.html_body:
                # Also modify HTML body if provided
                html_content = email.html_body
                if email.on_behalf_of:
                    html_signature = f"<br><br><strong>{email.on_behalf_of}</strong><br><br><em>Native IQ on behalf of {email.on_behalf_of}</em>"
                    html_content = f"{email.html_body}{html_signature}"
                
                text_part = MIMEText(body_content, 'plain')
                html_part = MIMEText(html_content, 'html')
                msg.attach(text_part)
                msg.attach(html_part)
            else:
                text_part = MIMEText(body_content, 'plain')
                msg.attach(text_part)

            # Add attachments if provided
            if email.attachments:
                for file_path in email.attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())
                            
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {os.path.basename(file_path)}"
                        )
                        msg.attach(part)

            # SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)

            recipients = [email.recipient]
            if email.cc:
                recipients.extend(email.cc)
            if email.bcc:
                recipients.extend(email.bcc)
            
            server.sendmail(self.sender_email, recipients, msg.as_string())
            server.quit()

            logger.info(f"Email sent successfully to {email.recipient}") 
            return {
                "success": True,
                "recipient": email.recipient,
                "subject": email.subject,
                "timestamp": datetime.now().isoformat(),
                "message_id": f"email_{datetime.now().timestamp()}"
            }   

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                "success": False,
                "error": str(e)
            }


email_service = EmailService()

@tool
def send_email(
    recipient: str,
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    html_body: str = "",
    attachments: Optional[List[str]] = None,
    sender: Optional[str] = None,
    on_behalf_of: Optional[str] = None
) -> str:
    """
    Send an email via SMTP.

    Args:
        recipient: The recipient of the email
        subject: The subject of the email
        body: The body of the email
        cc: Optional CC recipients (optional)
        bcc: Optional BCC recipients (optional)
        html_body: Optional HTML body of the email (optional)
        attachments: Optional attachments (optional)
        sender: Optional sender (optional)
        on_behalf_of: Native IQ on behalf of (username)
    """
    try:
        email_details = EmailDetails(
            recipient=recipient,
            subject=subject,
            body=body,
            cc=cc or [],
            bcc=bcc or [],
            html_body=html_body,
            attachments=attachments or [],
            sender=sender or "",
            on_behalf_of=on_behalf_of or ""
        )
        
        result = email_service.send_email(email_details)
        
        if result["success"]:
            behalf_info = f" on behalf of {on_behalf_of}" if on_behalf_of else ""
            return f"Email sent successfully{behalf_info} to {recipient}. Subject: '{subject}'. Message ID: {result['message_id']}"
        else:
            return f"Failed to send email to {recipient}. Error: {result['error']}"
            
    except Exception as e:
        logger.error(f"Error in send_email tool: {e}")
        return f"Error sending email: {str(e)}"

EMAIL_TOOLS = [
    send_email
]

def get_email_tools():
    """Get email tools."""
    return EMAIL_TOOLS
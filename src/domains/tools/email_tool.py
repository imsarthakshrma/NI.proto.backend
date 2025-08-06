
from email.mime.base import MIMEBase
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pydantic import Field

from langchain_core.tools import BaseTool

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


class SendEmailTool(BaseTool):

    recipient: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body content")
    cc: Optional[List[str]] = Field(description="CC email addresses", default=None)
    bcc: Optional[List[str]] = Field(description="BCC email addresses", default=None)
    html_body: Optional[str] = Field(description="HTML email body (optional)", default="")

class EmailService:

    def __init__(self):

        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('SMTP_EMAIL')
        self.sender_password = os.getenv('SMTP_PASSWORD')
        self.sender_name = os.getenv('SMTP_SENDER_NAME', 'Native AI')
    
    def send_email(self, email: EmailDetails) -> Dict[str, Any]:

        try:
            if not self.sender_email or not self.sender_password:
                return {
                    "success": False,
                    "error": "Email credentials not configured"
                }
            
            # create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = email.recipient
            msg['Subject'] = email.subject

            if email.cc:
                msg['Cc'] = ', '.join(email.cc)
            if email.bcc:
                msg['Bcc'] = ', '.join(email.bcc)
            
            # add body
            if email.html_body:
                text_part = MIMEText(email.body, 'plain')
                html_part = MIMEText(email.html_body, 'html')
                msg.attach(text_part)
                msg.attach(html_part)
            else:

                text_part = MIMEText(email.body, 'plain')
                msg.attach(text_part)

            # add attachments if provided
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

            

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    



import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    name: str = "send_email"
    description: str = "Send an email to a recipient"
    args_schema: Type[BaseModel] = EmailDetails

    # Implement the tool logic here
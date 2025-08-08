import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pydantic import Field
from datetime import datetime  
import logging

from langchain_core.tools import BaseTool, tool
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# google drive api scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

@dataclass
class DriveFile:

    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    created_time: Optional[str] = None
    modified_time: Optional[str] = None
    web_view_link: Optional[str] = None
    download_link: Optional[str] = None

    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticated()

    def _authenticated(self): 
       import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pydantic import Field

from langchain_core.tools import BaseTool, tool
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import io

logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

@dataclass
class DriveFile:
    """Represents a Google Drive file"""
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    created_time: Optional[str] = None
    modified_time: Optional[str] = None
    web_view_link: Optional[str] = None
    download_link: Optional[str] = None

class GoogleDriveService:
    """Google Drive API service wrapper"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        try:
            creds = None
            token_path = os.getenv('GOOGLE_DRIVE_TOKEN_PATH', 'token.json')
            credentials_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH', 'credentials.json')
            
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if os.path.exists(credentials_path):
                        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                        creds = flow.run_local_server(port=0)
                    else:
                        logger.error("Google Drive credentials file not found")
                        return
                
                
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.credentials = creds
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive service authenticated successfully")
            
        except Exception as e:
            logger.error(f"Failed to authenticate Google Drive: {e}")
            self.service = None

    def list_files(self, query: str = None, max_results: int = 10) -> List[DriveFile]:

        try:
            if not self.service:
                return []

            search_query = query if query else "trashed = false"

            results = self.service.files().list(
                q=search_query,
                pageSize=max_results,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)",
            ).execute()

            files = results.get("files", [])
            for file in files:
                drive_file = DriveFile(
                    id=file['id'],
                    name=file['name'],
                    mime_type=file['mimeType'],
                    size=int(file.get('size', 0)) if file.get('size') else None,
                    created_time=file.get('createdTime'),
                    modified_time=file.get('modifiedTime'),
                    web_view_link=file.get('webViewLink')
                )
                drive_file.append(drive_file)
            return drive_file

        except Exception as e:
            logger.error(f"Failed to list Drive files: {e}")
            return []

    def get_file_info(self, file_id: str) -> Optional[DriveFile]:
        try:
            if not self.service:
                return None
        
            file = self.service.files().get(fileId=file_id,
            fields="id, name,mimeType,size,createdTime,modifiedTime,webViewLink"
            ).execute()

            return DriveFile(
                id=file['id'],
                name=file['name'],
                mime_type=file['mimeType'],
                size=int(file.get('size', 0)) if file.get('size') else None,
                created_time=file.get('createdTime'),
                modified_time=file.get('modifiedTime'),
                web_view_link=file.get('webViewLink')
            )

        except Exception as e:
            logger.error(f"Failed to get Drive file info: {e}")
            return None

    def download_link(self, file_id: str, local_path: str) -> bool:

        try:
            if not self.service:
                return False

            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            with open(local_path, 'wb') as f:
                f.write(fh.getvalue())
            
            logger.info(f"File downloaded successfully to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return False
    
    def upload_file(self, local_path: str, drive_name: str = None, parent_folder_id: str = None) -> Optional[str]:

        try:
            if not self.service:
                return None
            
            if not os.path.exists(local_path):
                return None
            
            file_name = drive_name or os.path.basename(local_path)

            file_metadata = {
                'name': file_name
            }
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]

            media = MediaFileUpload(local_path, resumable=True)

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            logger.info(f"File uploaded successfully: {file['id']}")
            return file['id']
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return None

drive_service = GoogleDriveService()

@tool
def list_drive_files(query: str = "", max_results: int = 10) -> str:

    try:
        files = drive_service.list_files(query, max_results)

        if not files:
            return "No files found in Google Drive."

        result = f"Found {len(files)} files in Google Drive:\n\n"

        for i, file in enumerate(files, 1):
            size_info = f" ({file.size} bytes)" if file.size else ""
            result += f"{i}. **{file.name}**{size_info}\n"
            result += f"   ID: `{file.id}`\n"
            result += f"   Type: {file.mime_type}\n"
            if file.web_view_link:
                result += f"   Link: {file.web_view_link}\n"
            result += "\n"

        return result
    except Exception as e:
        logger.error(f"Failed to list Drive files: {e}", exc_info=True)
        return f"Failed to list Drive files: {str(e)}"
@tool
def get_drive_file_info(file_id: str) -> str:

    try:
        file = drive_service.get_file_info(file_id)
        
        if not file:
            return f"File not found with ID: {file_id}"
        
        result = f"**File Information:**\n\n"
        result += f"**Name:** {file.name}\n"
        result += f"**ID:** `{file.id}`\n"
        result += f"**Type:** {file.mime_type}\n"
        
        if file.size:
            result += f"**Size:** {file.size} bytes\n"
        if file.created_time:
            result += f"**Created:** {file.created_time}\n"
        if file.modified_time:
            result += f"**Modified:** {file.modified_time}\n"
        if file.web_view_link:
            result += f"**Link:** {file.web_view_link}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_drive_file_info tool: {e}")
        return f"Error getting file info: {str(e)}"

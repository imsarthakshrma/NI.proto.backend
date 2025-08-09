import os
import io
import logging
from dataclasses import dataclass
from typing import List, Optional

from langchain_core.tools import tool
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = ["https://www.googleapis.com/auth/drive"]


@dataclass
class DriveFile:
    """Represents a Google Drive file."""
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    created_time: Optional[str] = None
    modified_time: Optional[str] = None
    web_view_link: Optional[str] = None


class GoogleDriveService:
    """Google Drive API service wrapper."""

    def __init__(self) -> None:
        self.service = None
        self.credentials = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Google Drive API using OAuth2.

        Uses env vars:
        - GOOGLE_DRIVE_TOKEN_PATH (default: token.json)
        - GOOGLE_DRIVE_CREDENTIALS_PATH (default: credentials.json)
        """
        try:
            creds = None
            token_path = os.getenv("GOOGLE_DRIVE_TOKEN_PATH", "token.json")
            credentials_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH", "credentials.json")

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
                        logger.error("Google Drive credentials file not found: %s", credentials_path)
                        self.service = None
                        return

                # Save the credentials for the next run
                with open(token_path, "w") as token_file:
                    token_file.write(creds.to_json())

            self.credentials = creds
            self.service = build("drive", "v3", credentials=creds)
            logger.info("Google Drive service authenticated successfully")

        except Exception as e:
            logger.error("Failed to authenticate Google Drive: %s", e, exc_info=True)
            self.service = None

    def list_files(self, query: Optional[str] = None, max_results: int = 10) -> List[DriveFile]:
        """List files in Google Drive.

        Args:
            query: Optional Drive query (e.g., "name contains 'report' and trashed = false"). Defaults to "trashed = false".
            max_results: Max number of files to return.
        """
        try:
            if not self.service:
                return []

            search_query = query if query else "trashed = false"

            results = (
                self.service.files()
                .list(
                    q=search_query,
                    pageSize=max_results,
                    fields="files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)",
                )
                .execute()
            )

            files_meta = results.get("files", [])
            drive_files: List[DriveFile] = []
            for meta in files_meta:
                drive_files.append(
                    DriveFile(
                        id=meta.get("id"),
                        name=meta.get("name"),
                        mime_type=meta.get("mimeType"),
                        size=int(meta["size"]) if meta.get("size") else None,
                        created_time=meta.get("createdTime"),
                        modified_time=meta.get("modifiedTime"),
                        web_view_link=meta.get("webViewLink"),
                    )
                )
            return drive_files

        except Exception as e:
            logger.error("Failed to list Drive files: %s", e, exc_info=True)
            return []

    def get_file_info(self, file_id: str) -> Optional[DriveFile]:
        """Get detailed information for a file by ID."""
        try:
            if not self.service:
                return None

            file = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, mimeType, size, createdTime, modifiedTime, webViewLink",
                )
                .execute()
            )

            return DriveFile(
                id=file.get("id"),
                name=file.get("name"),
                mime_type=file.get("mimeType"),
                size=int(file["size"]) if file.get("size") else None,
                created_time=file.get("createdTime"),
                modified_time=file.get("modifiedTime"),
                web_view_link=file.get("webViewLink"),
            )

        except Exception as e:
            logger.error("Failed to get Drive file info: %s", e, exc_info=True)
            return None

    def download_file(self, file_id: str, local_path: str) -> bool:
        """Download a file from Google Drive to a local path."""
        try:
            if not self.service:
                return False

            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                # Optional: log progress via status.progress()

            with open(local_path, "wb") as f:
                f.write(fh.getvalue())

            logger.info("File downloaded successfully to %s", local_path)
            return True

        except Exception as e:
            logger.error("Failed to download file: %s", e, exc_info=True)
            return False

    def upload_file(
        self, local_path: str, drive_name: Optional[str] = None, parent_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """Upload a local file to Google Drive.

        Args:
            local_path: Path to the local file to upload.
            drive_name: Optional name for the uploaded file in Drive.
            parent_folder_id: Optional parent folder ID to upload into.
        Returns:
            The uploaded file's ID if successful, otherwise None.
        """
        try:
            if not self.service:
                return None

            if not os.path.exists(local_path):
                logger.error("Local file not found for upload: %s", local_path)
                return None

            file_name = drive_name or os.path.basename(local_path)
            file_metadata = {"name": file_name}
            if parent_folder_id:
                file_metadata["parents"] = [parent_folder_id]

            media = MediaFileUpload(local_path, resumable=True)

            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id, webViewLink")
                .execute()
            )

            logger.info("File uploaded successfully: %s", file.get("id"))
            return file.get("id")

        except Exception as e:
            logger.error("Failed to upload file: %s", e, exc_info=True)
            return None


# Singleton service instance
_drive_service = GoogleDriveService()


@tool
def list_drive_files(query: str = "", max_results: int = 10) -> str:
    """List files in Google Drive and return a human-readable summary string."""
    try:
        files = _drive_service.list_files(query or None, max_results)

        if not files:
            return "No files found in Google Drive."

        result = f"Found {len(files)} files in Google Drive:\n\n"
        for i, f in enumerate(files, 1):
            size_info = f" ({f.size} bytes)" if f.size else ""
            result += f"{i}. {f.name}{size_info}\n"
            result += f"   ID: `{f.id}`\n"
            result += f"   Type: {f.mime_type}\n"
            if f.web_view_link:
                result += f"   Link: {f.web_view_link}\n"
            result += "\n"

        return result
    except Exception as e:
        logger.error("Failed to list Drive files: %s", e, exc_info=True)
        return f"Failed to list Drive files: {str(e)}"

@tool
def get_drive_file_info(file_id: str) -> str:
    """Get a formatted string with Drive file details."""
    try:
        f = _drive_service.get_file_info(file_id)
        if not f:
            return f"File not found with ID: {file_id}"

        result = "**File Information:**\n\n"
        result += f"**Name:** {f.name}\n"
        result += f"**ID:** `{f.id}`\n"
        result += f"**Type:** {f.mime_type}\n"
        if f.size is not None:
            result += f"**Size:** {f.size} bytes\n"
        if f.created_time:
            result += f"**Created:** {f.created_time}\n"
        if f.modified_time:
            result += f"**Modified:** {f.modified_time}\n"
        if f.web_view_link:
            result += f"**Link:** {f.web_view_link}\n"
        return result

    except Exception as e:
        logger.error("Error in get_drive_file_info tool: %s", e, exc_info=True)
        return f"Error getting file info: {str(e)}"

@tool
def download_drive_file(file_id: str, local_path: str) -> str:
    """Download a Drive file to a local path and return a status message."""
    try:
        success = _drive_service.download_file(file_id, local_path)
        if success:
            return f"File downloaded successfully to: {local_path}"
        else:
            return f"Failed to download file with ID: {file_id}"
    except Exception as e:
        logger.error("Error in download_drive_file tool: %s", e, exc_info=True)
        return f"Error downloading file: {str(e)}"

@tool
def upload_drive_file(local_path: str, drive_name: str = "", parent_folder_id: str = "") -> str:
    """Upload a local file to Google Drive and return a status message."""
    try:
        file_id = _drive_service.upload_file(
            local_path,
            drive_name if drive_name else None,
            parent_folder_id if parent_folder_id else None,
        )
        if file_id:
            return f"File uploaded successfully to Google Drive. File ID: `{file_id}`"
        else:
            return f"Failed to upload file: {local_path}"
    except Exception as e:
        logger.error("Error in upload_drive_file tool: %s", e, exc_info=True)
        return f"Error uploading file: {str(e)}"


GOOGLE_DRIVE_TOOLS = [
    list_drive_files,
    get_drive_file_info,
    download_drive_file,
    upload_drive_file,
]

def get_google_drive_tools():
    """Return the list of Google Drive tools."""
    return GOOGLE_DRIVE_TOOLS
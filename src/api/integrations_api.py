"""
Integration API - OAuth flows for Google services
Handles user authentication and service connection from frontend
"""

import os
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import sys

# Add project paths
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in [str(SRC), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from services.cache_service import cache_service

router = APIRouter(prefix="/api/integrations", tags=["Integrations"])

# OAuth configuration
SCOPES = {
    "gmail": [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly"
    ],
    "calendar": [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events"
    ],
    "drive": [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
}

# Pydantic models
class IntegrationStatus(BaseModel):
    service: str
    connected: bool
    email: Optional[str] = None
    last_connected: Optional[str] = None
    permissions: List[str] = []

class OAuthResponse(BaseModel):
    auth_url: str
    state: str
    service: str

class ConnectionResult(BaseModel):
    success: bool
    service: str
    user_email: Optional[str] = None
    message: str

class ServiceInfo(BaseModel):
    name: str
    display_name: str
    description: str
    scopes: List[str]
    connected: bool

def get_oauth_flow(service: str, redirect_uri: str) -> Flow:
    """Create OAuth flow for specified service"""
    credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    
    if not os.path.exists(credentials_file):
        raise HTTPException(
            status_code=500, 
            detail="Google credentials file not found. Please configure OAuth credentials."
        )
    
    scopes = SCOPES.get(service, [])
    if not scopes:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    
    flow = Flow.from_client_secrets_file(
        credentials_file,
        scopes=scopes,
        redirect_uri=redirect_uri
    )
    
    return flow

async def get_user_credentials(user_id: str, service: str) -> Optional[Credentials]:
    """Get stored credentials for user and service"""
    cache_key = f"{user_id}_{service}_credentials"
    creds_data = await cache_service.get("oauth", cache_key)
    
    if not creds_data:
        return None
    
    credentials = Credentials(
        token=creds_data.get("token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri=creds_data.get("token_uri"),
        client_id=creds_data.get("client_id"),
        client_secret=creds_data.get("client_secret"),
        scopes=creds_data.get("scopes")
    )
    
    # Refresh if expired
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleRequest())
        await store_user_credentials(user_id, service, credentials)
    
    return credentials

async def store_user_credentials(user_id: str, service: str, credentials: Credentials):
    """Store user credentials securely"""
    cache_key = f"{user_id}_{service}_credentials"
    
    creds_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
    
    # Store for 30 days
    await cache_service.set("oauth", cache_key, creds_data, ttl=30*24*3600)

@router.get("/services")
async def get_available_services():
    """Get list of available integration services"""
    services = [
        ServiceInfo(
            name="gmail",
            display_name="Gmail",
            description="Send emails and access inbox",
            scopes=SCOPES["gmail"],
            connected=False
        ),
        ServiceInfo(
            name="calendar",
            display_name="Google Calendar",
            description="Schedule meetings and manage events",
            scopes=SCOPES["calendar"],
            connected=False
        ),
        ServiceInfo(
            name="drive",
            display_name="Google Drive",
            description="Access and share files",
            scopes=SCOPES["drive"],
            connected=False
        )
    ]
    
    return {"services": services}

@router.get("/status/{user_id}")
async def get_integration_status(user_id: str):
    """Get integration status for all services"""
    statuses = []
    
    for service in SCOPES.keys():
        credentials = await get_user_credentials(user_id, service)
        
        status = IntegrationStatus(
            service=service,
            connected=credentials is not None,
            permissions=SCOPES[service] if credentials else []
        )
        
        # Get user email if connected
        if credentials:
            try:
                if service == "gmail":
                    gmail_service = build("gmail", "v1", credentials=credentials)
                    profile = gmail_service.users().getProfile(userId="me").execute()
                    status.email = profile.get("emailAddress")
                elif service == "calendar":
                    calendar_service = build("calendar", "v3", credentials=credentials)
                    # Could get calendar info here
                    pass
                
                status.last_connected = datetime.now().isoformat()
            except Exception:
                # Credentials might be invalid
                status.connected = False
        
        statuses.append(status)
    
    return {"integrations": statuses}

@router.post("/connect/{service}")
async def initiate_oauth_flow(
    service: str,
    user_id: str,
    frontend_url: str = Query(..., description="Frontend URL for redirect")
):
    """Initiate OAuth flow for a service"""
    
    # Validate service
    if service not in SCOPES:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    
    # Create redirect URI
    redirect_uri = f"{frontend_url.rstrip('/')}/auth/callback"
    
    try:
        flow = get_oauth_flow(service, redirect_uri)
        
        # Generate state parameter for security
        state = secrets.token_urlsafe(32)
        
        # Store state and user info temporarily
        state_data = {
            "user_id": user_id,
            "service": service,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now().isoformat()
        }
        await cache_service.set("oauth_state", state, state_data, ttl=600)  # 10 minutes
        
        # Get authorization URL
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state
        )
        
        return OAuthResponse(
            auth_url=auth_url,
            state=state,
            service=service
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate OAuth flow: {str(e)}")

@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None)
):
    """Handle OAuth callback from Google"""
    
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    # Retrieve state data
    state_data = await cache_service.get("oauth_state", state)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
    
    user_id = state_data["user_id"]
    service = state_data["service"]
    redirect_uri = state_data["redirect_uri"]
    
    try:
        # Complete OAuth flow
        flow = get_oauth_flow(service, redirect_uri)
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Store credentials
        await store_user_credentials(user_id, service, credentials)
        
        # Get user info
        user_email = None
        if service == "gmail":
            gmail_service = build("gmail", "v1", credentials=credentials)
            profile = gmail_service.users().getProfile(userId="me").execute()
            user_email = profile.get("emailAddress")
        
        # Clean up state
        await cache_service.delete("oauth_state", state)
        
        # Return success page or redirect to frontend
        return ConnectionResult(
            success=True,
            service=service,
            user_email=user_email,
            message=f"Successfully connected {service.title()}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete OAuth flow: {str(e)}")

@router.delete("/disconnect/{user_id}/{service}")
async def disconnect_service(user_id: str, service: str):
    """Disconnect a service for user"""
    
    if service not in SCOPES:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    
    # Remove stored credentials
    cache_key = f"{user_id}_{service}_credentials"
    success = await cache_service.delete("oauth", cache_key)
    
    return {
        "success": success,
        "service": service,
        "message": f"Disconnected {service.title()}"
    }

@router.get("/test/{user_id}/{service}")
async def test_service_connection(user_id: str, service: str):
    """Test if service connection is working"""
    
    credentials = await get_user_credentials(user_id, service)
    if not credentials:
        raise HTTPException(status_code=404, detail=f"{service.title()} not connected")
    
    try:
        if service == "gmail":
            gmail_service = build("gmail", "v1", credentials=credentials)
            profile = gmail_service.users().getProfile(userId="me").execute()
            return {
                "service": service,
                "status": "connected",
                "email": profile.get("emailAddress"),
                "message": "Gmail connection working"
            }
            
        elif service == "calendar":
            calendar_service = build("calendar", "v3", credentials=credentials)
            calendars = calendar_service.calendarList().list().execute()
            return {
                "service": service,
                "status": "connected",
                "calendars_count": len(calendars.get("items", [])),
                "message": "Calendar connection working"
            }
            
        elif service == "drive":
            drive_service = build("drive", "v3", credentials=credentials)
            about = drive_service.about().get(fields="user").execute()
            return {
                "service": service,
                "status": "connected",
                "user": about.get("user", {}).get("emailAddress"),
                "message": "Drive connection working"
            }
            
    except Exception as e:
        return {
            "service": service,
            "status": "error",
            "message": f"Connection test failed: {str(e)}"
        }

@router.post("/refresh/{user_id}/{service}")
async def refresh_service_credentials(user_id: str, service: str):
    """Manually refresh service credentials"""
    
    credentials = await get_user_credentials(user_id, service)
    if not credentials:
        raise HTTPException(status_code=404, detail=f"{service.title()} not connected")
    
    try:
        if credentials.refresh_token:
            credentials.refresh(GoogleRequest())
            await store_user_credentials(user_id, service, credentials)
            
            return {
                "success": True,
                "service": service,
                "message": "Credentials refreshed successfully"
            }
        else:
            return {
                "success": False,
                "service": service,
                "message": "No refresh token available. Please reconnect."
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh credentials: {str(e)}")

@router.get("/permissions/{user_id}")
async def get_user_permissions(user_id: str):
    """Get detailed permissions for all connected services"""
    permissions = {}
    
    for service in SCOPES.keys():
        credentials = await get_user_credentials(user_id, service)
        
        if credentials:
            permissions[service] = {
                "connected": True,
                "scopes": credentials.scopes or SCOPES[service],
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
                "has_refresh_token": bool(credentials.refresh_token)
            }
        else:
            permissions[service] = {
                "connected": False,
                "scopes": [],
                "expires_at": None,
                "has_refresh_token": False
            }
    
    return {"permissions": permissions}

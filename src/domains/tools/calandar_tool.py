"""
Google Calendar Integration Tool for DELA AI
Handles calendar operations and meeting scheduling
"""

import os
import logging
from datetime import datetime, timedelta
from this import d
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from langchain.tools import BaseTool
from langchain_core.tools import tool
import json

# google calendar api imports
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logging.warning("Google Calendar API not available. Install google-api-python-client")

logger = logging.getLogger(__name__)


@dataclass
class MeetingDetails:
    """Meeting details structure"""
    title: str
    start_time: datetime
    end_time: datetime
    attendees: List[str]
    description: str = ""
    location: str = ""
    meeting_type: str = "business"

@dataclass
class TimeSlot:
    """Available time slot"""
    start_time: datetime
    end_time: datetime
    # attendees: List[str]
    duration_minutes: int


class ScheduleMeetingInput(BaseModel):
    """Input schema for scheduling meetings"""
    title: str = Field(description="Meeting title")
    start_time: str = Field(description="Start time in ISO format (YYYY-MM-DDTHH:MM:SS)")
    duration_minutes: int = Field(description="Meeting duration in minutes", default=60)
    attendees: List[str] = Field(description="List of attendee email addresses")
    description: str = Field(description="Meeting description", default="")
    location: str = Field(description="Meeting location", default="")

class FindFreeSlotsInput(BaseModel):
    """Input schema for finding free time slots"""
    duration_minutes: int = Field(description="Required meeting duration in minutes", default=60)
    days_ahead: int = Field(description="Number of days to look ahead", default=7)
    preferred_times: Optional[List[str]] = Field(description="Preferred time slots (e.g., 'morning', 'afternoon')", default=None)


class GetMeetingsInput(BaseModel):
    """Input schema for getting upcoming meetings"""
    days_ahead: int = Field(description="Number of days to look ahead", default=7)

class GoogleCalendarService: 
    """Google Calendar service for scheduling and managing meetings"""

    def __init__(self):
        self.service = None
        self.credentials = None
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        self.default_calendar_id = 'primary'
        self.business_hours_start = 9  # 9 AM
        self.business_hours_end = 18   # 6 PM

        if GOOGLE_AVAILABLE:
            self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Calendar service"""
        try:
            self.credentials = self._load_credentials()

            if self.credentials and self.credentials.valid:
                self.service = build('calendar', 'v3', credentials=self.credentials)
                logger.info("Google Calendar service initialized successfully")
            else:
                logger.warning("Google Calendar credentials not valid")
                
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {e}")


    def _load_credentials(self) -> Optional[Credentials]:
        """Load Google Calendar credentials"""
        try:
            token_path = os.getenv('GOOGLE_CALENDAR_TOKEN_PATH', 'token.json')
            credentials_path = os.getenv('GOOGLE_CALENDAR_CREDENTIALS_PATH', 'credentials.json')
            
            creds = None
            
            # load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.scopes)
            
            # if no valid credentials, run auth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if os.path.exists(credentials_path):
                        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.scopes)
                        creds = flow.run_local_server(port=0)
                    else:
                        logger.error(f"Credentials file not found: {credentials_path}")
                        return None
                
                # save credentials
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            return creds
            
        except Exception as e:
            logger.error(f"Error loading Google Calendar credentials: {e}")
            return None

    async def create_meeting(
        self,
        meeting: MeetingDetails
    ) -> Optional[Dict[str, Any]]:
        """Create a calendar meeting"""

        if not self.service:
            logger.error("Google Calendar service not initialized")
            return None

        try:
            event = {
                'summary': meeting.title,
                'description': meeting.description,
                'start': {
                    'dateTime': meeting.start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': meeting.end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [{'email': email} for email in meeting.attendees],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 15},
                    ],
                },
            }

            if meeting.location:
                event['location'] = meeting.location

            created_event = self.service.events().insert(
                calendarId=self.default_calendar_id,
                body=event,
                sendUpdates='all'
            ).execute()

            return {
                'event_id': created_event.get('id'),
                'html_link': created_event.get('htmlLink'),
                'status': 'created',
                'title': meeting.title,
                'start_time': meeting.start_time.isoformat(),
                'attendees': meeting.attendees
            }

        except HttpError as e:
            logger.error(f"HTTP error creating meeting: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating meeting: {e}")
            return None
        
    async def find_free_slots(self, duration_minutes: int = 60, days_ahead: int = 7) -> List[TimeSlot]:
        """Find available time slots"""
        if not self.service:
            logger.error("Google Calendar service not available")
            return []

        try:
            now = datetime.now()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

            freebusy_query = {
                'timeMin': time_min,
                'timeMax': time_max,
                'items': [{'id': self.default_calendar_id}]
            }

            freebusy_result = self.service.freebusy().query(body=freebusy_query).execute()
            busy_times = freebusy_result['calendars'][self.default_calendar_id]['busy']

            free_slots = []
            current_time = now.replace(minute=0, second=0, microsecond=0)

            for day in range(days_ahead):
                day_start = current_time.replace(hour=self.business_hours_start) + timedelta(days=day)
                day_end = current_time.replace(hour=self.business_hours_end) + timedelta(days=day)

                if day_start.weekday() >= 5: # skip weekends
                    continue

                while slot_start + timedelta(minutes=duration_minutes) <= day_end:
                    slot_end = slot_start + timedelta(minutes=duration_minutes)

                    is_free = True
                    for busy in busy_times:
                        busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                        busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                        
                        if (slot_start < busy_end and slot_end > busy_start):
                            is_free = False
                            break
                    
                    if is_free:
                        free_slots.append(TimeSlot(
                            start_time=slot_start,
                            end_time=slot_end,
                            duration_minutes=duration_minutes
                        ))
                    
                    slot_start += timedelta(minutes=30)
            logger.info(f"Found {len(free_slots)} free slots")
            return free_slots[:10]

        except Exception as e:
            logger.error(f"Error finding free slots: {e}")
            return []

    async def get_upcoming_meetings(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming meetings"""

        if not self.service:
            return []
        
        try:
            now = datetime.now()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=self.default_calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=20,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            meetings = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                meetings.append({
                    'id': event['id'],
                    'title': event.get('summary', 'No Title'),
                    'start_time': start,
                    'attendees': [att.get('email') for att in event.get('attendees', [])],
                    'location': event.get('location', ''),
                    'html_link': event.get('htmlLink', '')
                })
            
            return meetings
            
        except Exception as e:
            logger.error(f"Error getting upcoming meetings: {e}")
            return []
        
# GLOBAL CALENDAR SERVICE INSTANCE
calendar_service = GoogleCalendarService()


@tool("schedule_meeting", args_schema=ScheduleMeetingInput)

async 
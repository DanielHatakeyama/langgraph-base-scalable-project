import os
import os.path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

import pytz
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pydantic import BaseModel, ValidationError, validator
from langchain.tools import tool

# ------------------------------------------------------------------------------
# Google Authentication and Service Setup
# ------------------------------------------------------------------------------

# Load environment variables early
load_dotenv()

# Google Calendar API scope
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
_service_cache = None  # Cache the service object once created

def get_calendar_service():
    """
    Returns a Google Calendar API service object.
    Caches the service after the first creation.
    """
    global _service_cache
    if _service_cache:
        return _service_cache

    creds = None
    # Check if token file exists to load previously saved credentials
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If no valid credentials are available, start the authorization flow.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_config = {
                "installed": {
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost")]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    _service_cache = build('calendar', 'v3', credentials=creds)
    return _service_cache

# ------------------------------------------------------------------------------
# Calendar Event Tool
# ------------------------------------------------------------------------------

class CreateCalendarEventInputModel(BaseModel):
    topic: str
    start_time: datetime
    end_time: datetime

    @validator("end_time")
    def ensure_end_after_start(cls, v, values):
        if "start_time" in values and v <= values["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


@tool
def create_calendar_event_tool(event_data: Dict[str, Any]) -> str:
    """
    Creates a Google Calendar event from the provided event_data dictionary.

    Args:
        event_data (dict): Dictionary with the following keys:
            - topic: str
            - start_time: datetime (or ISO-formatted string)
            - end_time: datetime (or ISO-formatted string)

    Returns:
        str: A message indicating the event's creation status or an error message.
    """
    try:
        data = CreateCalendarEventInputModel(**event_data)
    except ValidationError as e:
        return f"Input validation error: {e}"

    service = get_calendar_service()
    event_body = {
        'summary': data.topic,
        'start': {'dateTime': data.start_time.isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': data.end_time.isoformat(), 'timeZone': 'UTC'},
    }

    try:
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        return f"Event created: {created_event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event: {e}"


class CreateCalendarEventModel(BaseModel):
    """
    Validates the JSON string for event creation.
    """
    topic: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None


@tool
def create_calendar_event(event_data_json: str) -> str:
    """
    Expects a JSON string with at least "topic" and "start_time".
    Example:
        {
          "topic": "Team Meeting",
          "start_time": "2025-02-15T10:00:00Z",
          "end_time": "2025-02-15T11:00:00Z",
          "location": "Conference Room A",
          "description": "Weekly sync-up"
        }

    Returns:
        str: A message indicating the event's creation status or an error message.
    """
    # 1) Parse JSON
    try:
        event_data = json.loads(event_data_json)
    except json.JSONDecodeError:
        return "Invalid JSON input. Please provide a valid JSON string."

    # 2) Validate with Pydantic
    try:
        data = CreateCalendarEventInputModel(**event_data)
    except ValidationError as e:
        return f"Input validation error: {e}"

    service = get_calendar_service()

    # If end_time not given, reuse start_time or pick a default
    end_time = data.end_time or (data.start_time + timedelta(hours=1))

    event_body = {
        'summary': data.topic,
        'start': {
            'dateTime': data.start_time.isoformat(),
            'timeZone': 'UTC'
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC'
        },
    }
    # Safely set the 'location' if it exists and is truthy
    if getattr(data, "location", None):
        event_body["location"] = data.location

    # Safely set the 'description' if it exists and is truthy
    if getattr(data, "description", None):
        event_body["description"] = data.description


    # 3) Attempt to create the event
    try:
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        return f"Event created: {created_event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event: {e}"

# WHAT THE FUCK IS THIS FUNCTION LMFAO

# Honstly fuck you im hard coding time zone 
@tool
def get_current_datetime():
    """
    Return the current date and time in ISO 8601 format using Mountain Time (America/Denver).
    """
    tz = pytz.timezone("America/Denver")
    now = datetime.datetime.now(tz).isoformat()

    print("asdfasdf")

    return now

# ------------------------------------------------------------------------------
# Current Time Tool
# ------------------------------------------------------------------------------

class GetCurrentTimeInputModel(BaseModel):
    time_zone: Optional[str] = "UTC"

@tool
def get_current_time_tool(input_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Returns the current time in the specified time zone.
    If no time zone is provided, it defaults to UTC.

    Args:
        input_data (dict, optional): Dictionary with an optional 'time_zone' key.

    Returns:
        str: A message with the current time or an error message.
    """
    input_data = input_data or {}

    try:
        data = GetCurrentTimeInputModel(**input_data)
    except ValidationError as e:
        return f"Input validation error: {e}"
    
    try:
        tz = pytz.timezone(data.time_zone)
    except Exception as e:
        return f"Invalid time zone: {e}"

    now = datetime.now(tz)
    return f"Current time in {data.time_zone} is: {now.isoformat()}"


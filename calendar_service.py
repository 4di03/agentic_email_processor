from __future__ import annotations
from zoneinfo import ZoneInfo
from email_summarizer import _create_default_event_time_info
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from email_summarizer import Timezone, EventTimeInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google_creds import get_google_client_creds
@dataclass
class CalendarEvent:
    title: str
    description: str = ""
    event_time_info : EventTimeInfo | None = None


CALENDAR_ID = "6f5d5b2a13964e30d423ef619b4bdb33d81b9abd9cf1d523b4d723e317b187a4@group.calendar.google.com"

from logger import logged_class
@logged_class
class CalendarService:
    """Uses Google Calendar API (events) and Google Tasks API (tasks)."""

    def __init__(
        self,
        *,
        calendar_id: str = CALENDAR_ID,
        #tasklist_id: str = "@default",
        default_timezone: Timezone = Timezone.PST,
    ):
        self.calendar_id = calendar_id
        #self.tasklist_id = tasklist_id
        self.default_timezone = default_timezone

        creds = get_google_client_creds()
        # Cache service clients
        self._calendar = build("calendar", "v3", credentials=creds)
        self._tasks = build("tasks", "v1", credentials=creds)

    def create_event(self, event: CalendarEvent) -> str:
        """
        Creates a calendar event or a Google Task.
        Returns the created resource ID (event id or task id).
        """
        # if event.is_task:
        #     return self._create_task(event)

        # Calendar events: need start/end; if missing, make a 30-min event "now"
        if not event.event_time_info:
            event.event_time_info = _create_default_event_time_info()
        start, end = self._normalize_times(event.event_time_info.start_time, event.event_time_info.end_time)

        body = {
            "summary": event.title,
            "description": event.description or "",
            "start": {"dateTime": start.isoformat(), "timeZone": self.default_timezone.value},
            "end": {"dateTime": end.isoformat(), "timeZone": self.default_timezone.value},
        }

        created = self._calendar.events().insert(calendarId=self.calendar_id, body=body).execute()
        return created["id"]

    # ----------------- internal helpers -----------------

    # def _create_task(self, event: CalendarEvent) -> str:
    #     """
    #     Creates a Google Task (NOT a Calendar event).
    #     Uses Tasks API.
    #     """
    #     task_body = {
    #         "title": event.title,
    #         "notes": event.description or "",
    #     }

    #     # Tasks support "due" (RFC3339). If you pass a datetime, it becomes a due time.
    #     if event.start_time is not None:
    #         due = self._ensure_tz(event.start_time).isoformat()
    #         task_body["due"] = due

    #     created = self._tasks.tasks().insert(tasklist=self.tasklist_id, body=task_body).execute()
    #     return created["id"]


    def _ensure_tz(self, dt: datetime) -> datetime:
        tz = ZoneInfo(self.default_timezone.value)  # e.g. "America/Los_Angeles"

        if dt.tzinfo is None:
            # naive → assume default timezone
            return dt.replace(tzinfo=tz)
        else:
            # aware → convert
            return dt.astimezone(tz)

    def _normalize_times(
        self,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        if start is None and end is None:
            start = now
            end = now.replace(minute=now.minute + 30)  # simple default
        elif start is not None and end is None:
            start = self._ensure_tz(start)
            end = start.replace(minute=start.minute + 30)  # simple default
        elif start is None and end is not None:
            end = self._ensure_tz(end)
            start = end.replace(minute=end.minute - 30)  # simple default
        else:
            start = self._ensure_tz(start)
            end = self._ensure_tz(end)
        return start, end
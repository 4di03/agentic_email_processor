from datetime import datetime, timedelta, timezone
from calendar_service import CalendarService, CalendarEvent, EventTimeInfo
from email_summarizer import Timezone
CALENDAR_CREDENTIALS_PATH = "secrets/calendar_credentials.json"

if __name__ == "__main__":
    svc = CalendarService()

    # Create a calendar event
    event_id = svc.create_event(
        CalendarEvent(
            title="Coffee chat",
            description="Catch up with Sam",
            event_time_info=EventTimeInfo(
                start_time=datetime.now(timezone.utc) + timedelta(hours=2),
                end_time=datetime.now(timezone.utc) + timedelta(hours=3),
                timezone=Timezone.PST
            )
        )
    )
    print("Created event:", event_id)


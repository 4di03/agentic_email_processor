

from db import FileDB
from calendar_service import CalendarService, CalendarEvent, EventTimeInfo
from email_summarizer import EmailSummarizer, Timezone, EmailSummaryResponseFormat, init_email_summarizer
from llm_service import BaseChatModel
from logger import Logger
from datetime import datetime, timezone, timedelta
def init_email_to_event_service(
    model : BaseChatModel,
    with_critic: bool = False,
    dry_run : bool = True,
) -> "EmailToEventService":
    return EmailToEventService(
        calendar_service=CalendarService(),
        email_summarizer=init_email_summarizer(model = model, with_critic= with_critic),
        dry_run= dry_run,
    )

logger = Logger(context = "EmailToEventService", debug=True)
from logger import logged_class
@logged_class
class EmailToEventService:
    def __init__(self, calendar_service: CalendarService, email_summarizer : EmailSummarizer, dry_run : bool = True):
        self.calendar_service = calendar_service
        self.email_summarizer = email_summarizer
        self.dry_run = dry_run # if true, don't actually create events in calendar, just print them.
        self.email_db = FileDB("processed_emails_db.txt")  # to track processed emails
        self.email_db.connect()

    def __del__(self):
        self.email_db.disconnect()

    def _email_summary_to_event(self, email: EmailSummaryResponseFormat) -> CalendarEvent | None:
        if not email.is_important:
            return None
        # Extract event details from email (this is a placeholder; actual implementation may vary)

        return CalendarEvent(
            title= email.email.subject if email.email else "No Subject",
            description= email.email.body if email.email else "No Body",
            event_time_info= email.event_time_info
        )
    
    async def _summarize_recent_emails(self, lookback_hours = 24):
        """
        Summarizes recent emails that haven't been processed yet in the last lookback_hours.
        """
        # get emails from last lookback_hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        recent_emails = list(self.email_summarizer.email_service.get_recent_emails(cutoff_time=cutoff_time))
        unprocessed_emails = list(filter(lambda email: not self.email_db.get(email.message_id), recent_emails)) # filter out emails we have already made events for


        return await self.email_summarizer._summarize_emails_async(unprocessed_emails)

    async def process_emails(self, lookback_hours = 24) -> list[str]:
        # TODO: implemenet write-ahead log on db to allow for smoother recovery in case of failure mid-processing

        # leverages async event loop for llm calls for email summarization
        created_event_ids = []
        email_summaries = await self._summarize_recent_emails(lookback_hours=lookback_hours)
        for email_summary in email_summaries:
            event = self._email_summary_to_event(email_summary)
            if event:
                if self.dry_run:
                    logger.log(f"Created Event: {event}")
                    continue
                event_id = self.calendar_service.create_event(event)
                # mark email as processed
                self.email_db.put(email_summary.email.message_id, True)

                created_event_ids.append(event_id)


        return created_event_ids

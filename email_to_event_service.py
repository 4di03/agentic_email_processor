


from calendar_service import CalendarService, CalendarEvent, EventTimeInfo
from email_summarizer import EmailSummarizer, Timezone, EmailSummaryResponseFormat, init_email_summarizer
from llm_service import BaseChatModel

def init_email_to_event_service(
    model : BaseChatModel,
    with_critic: bool = False,
) -> "EmailToEventService":
    return EmailToEventService(
        calendar_service=CalendarService(),
        email_summarizer=init_email_summarizer(model = model, with_critic= with_critic)
    )


class EmailToEventService:
    def __init__(self, calendar_service: CalendarService, email_summarizer : EmailSummarizer):
        self.calendar_service = calendar_service
        self.email_summarizer = email_summarizer

    def _email_summary_to_event(self, email: EmailSummaryResponseFormat) -> CalendarEvent | None:
        if not email.is_important:
            return None
        # Extract event details from email (this is a placeholder; actual implementation may vary)

        return CalendarEvent(
            title= email.email.subject if email.email else "No Subject",
            description= email.email.body if email.email else "No Body",
            event_time_info= email.event_time_info
        )
    
    async def process_emails(self, lookback_hours = 24) -> list[str]:
        # leverages async event loop for llm calls for email summarization
        created_event_ids = []
        email_summaries = await self.email_summarizer.summarize_recent_emails(lookback_hours=lookback_hours)
        for email_summary in email_summaries:
            event = self._email_summary_to_event(email_summary)
            if event:
                event_id = self.calendar_service.create_event(event)
                created_event_ids.append(event_id)
        return created_event_ids

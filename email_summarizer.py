

from email_service import EmailService, Email
from llm_service import LLMService

DEBUG = True
SUMMARIZER_PROMPT_PATH = "prompts/email_summarizer.txt"
SINGLE_SUMMARY_PROMPT_PATH = "prompts/single_email_summary.txt"
class EmailSummarizer:
    SUMMARIZER_PROMPT_TEMPLATE = open(SUMMARIZER_PROMPT_PATH, 'r').read()
    SINGLE_SUMMARY_PROMPT_TEMPLATE = open(SINGLE_SUMMARY_PROMPT_PATH, 'r').read()
    def __init__(self, llm_service, email_service):
        self.llm_service = llm_service
        self.email_service = email_service

    def _summarize_emails(self, emails : list[Email]):
        combined_email_bodies = "\n\n".join(
            [self._summarize_single_email(email) for email in emails]
        )
        prompt = self.SUMMARIZER_PROMPT_TEMPLATE.replace("{emails}", combined_email_bodies)
        summary = self.llm_service.generate_text(prompt)
        return summary
    
    def _summarize_single_email(self, email : Email):
        prompt = self.SINGLE_SUMMARY_PROMPT_TEMPLATE.replace(
            "{email}", str(email)
        )
        summary = self.llm_service.generate_text(prompt)
        if (DEBUG):
            print("Single Email Summary:", summary)
        return summary
    
    def summarize_last_n_emails(self, n=5):
        emails = list(self.email_service.get_last_n_emails(n=n))
        
        return self._summarize_emails(emails)


from email_service import EmailService, Email
from llm_service import LLMService

import re
from html import unescape
from logger import Logger
def strip_html_and_urls(text: str) -> str:
    """
    Removes HTML tags and URLs from the given text.
    """
    if not text:
        return ""

    # Decode HTML entities (&nbsp;, &amp;, etc.)
    text = unescape(text)

    # Remove script and style blocks completely
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove all HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove URLs (http, https, www)
    text = re.sub(
        r"https?://\S+|www\.\S+",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


DEBUG = False
SUMMARIZER_PROMPT_PATH = "prompts/email_summarizer.txt"
SINGLE_SUMMARY_PROMPT_PATH = "prompts/single_email_summary.txt"

logger = Logger(context = "EmailSummarizer", debug=DEBUG)

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
        email_str = strip_html_and_urls(str(email))
        logger.log("Summarizing Email:\n" + email_str)

        prompt = self.SINGLE_SUMMARY_PROMPT_TEMPLATE.replace(
            "{email}", email_str
        )
        summary = self.llm_service.generate_text(prompt)
        logger.log("Single Email Summary: " + summary)

        return summary
    
    def summarize_last_n_emails(self, n=5):
        emails = list(self.email_service.get_last_n_emails(n=n))
        
        return self._summarize_emails(emails)
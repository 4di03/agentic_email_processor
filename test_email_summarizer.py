from email_summarizer import EmailSummarizer
from llm_service import LocalLlamaService
from email_service import EmailService, Email
from logger import Logger


logger = Logger(context = "TestEmailSummarizer", debug=True)
if __name__ == "__main__":
    llm_service = LocalLlamaService()
    email_service = EmailService.create_email_service() 
    email_summarizer = EmailSummarizer(llm_service, email_service)
    summary = email_summarizer.summarize_last_n_emails(n=5)
    logger.log("Email Summary:\n" + summary)
from email_summarizer import EmailSummarizer,init_email_summarizer
from llm_service import LocalLlamaService, LangchainAdapter
from email_service import EmailService, Email
from logger import Logger
from langchain.chat_models import init_chat_model


llama = LangchainAdapter(llm = LocalLlamaService())
claude_sonnet = init_chat_model(
        "claude-sonnet-4-5-20250929",
        temperature=0,
        timeout=30,
        max_tokens=1000,
    )
haiku = init_chat_model(
    "claude-3-5-haiku-20241022",  # cheaper Claude Haiku
    timeout=30,
    temperature=0,
    max_tokens=1000
)
logger = Logger(context = "TestEmailSummarizer", debug=True)
if __name__ == "__main__":
    email_summarizer = init_email_summarizer(haiku, with_critic=True)
    summary = email_summarizer.summarize_last_n_emails(n=5)
    for email_summary in summary:
        if email_summary.is_important:
            logger.log("Important Email:\n" + str(email_summary.email))
        else:
            logger.log("Not Important Email, skipping detailed summary.")
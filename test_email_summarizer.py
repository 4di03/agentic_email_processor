from email_summarizer import EmailSummarizer, _init_email_summarizer_agent, _init_critic_agent
from llm_service import LocalLlamaService, LangchainAdapter
from email_service import EmailService, Email
from logger import Logger
from langchain.chat_models import init_chat_model

llama = LangchainAdapter(llm = LocalLlamaService())
claude_sonnet = init_chat_model(
        "claude-sonnet-4-5-20250929",
        temperature=0,
        timeout=10,
        max_tokens=1000
    )
haiku = init_chat_model(
    "claude-3-5-haiku-20241022",  # cheaper Claude Haiku
    temperature=0,
    timeout=10,
    max_tokens=1000
)
logger = Logger(context = "TestEmailSummarizer", debug=True)
if __name__ == "__main__":
    agent = _init_email_summarizer_agent(haiku)
    critic_agent = _init_critic_agent(haiku)
    email_service = EmailService.create_email_service() 
    email_summarizer = EmailSummarizer(agent, email_service, critic_agent=_init_critic_agent(haiku))
    summary = email_summarizer.summarize_last_n_emails(n=5)
    for email_summary in summary:
        if email_summary.is_important:
            logger.log("Important Email:\n" + str(email_summary.email))
        else:
            logger.log("Not Important Email, skipping detailed summary.")
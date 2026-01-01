from enum import Enum
from datetime import datetime
import asyncio
from logger import logged_class
from db import FileDB
from anthropic import RateLimitError
import random
from email_service import EmailService, Email
from langgraph.graph.state import CompiledStateGraph
from dataclasses import dataclass
from langchain.chat_models.base import BaseChatModel
import re
from html import unescape
from logger import Logger
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import SystemMessage
from langchain_core.callbacks import BaseCallbackHandler
from datetime import datetime, timedelta, timezone
from logger import logged_class, Logger
from constants import TIMEOUTS_SECONDS

MAX_CHARS_PER_EMAIL = 1000
DEFAULT_CONCURRENCY = 5

def _init_summarizer_prompt() -> str:
    """
    loads and initializes the email summarizer system prompt with dynamic policy information.
    """
    base_prompt = open("prompts/single_email_summarizer_system_prompt.txt").read()
    
    policy_text_lines = []
    # add current timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    policy_text_lines.append(f"- Current Time: {current_time} (in UTC)")
    

    return base_prompt.replace("{dynamic_policy}", "\n".join(policy_text_lines))

DEBUG = False
SUMMARIZER_SYSTEM_PROMPT_TEMPLATE =_init_summarizer_prompt()
CRITIC_SYSTEM_PROMPT = open("prompts/critic_prompt.txt").read()
logger = Logger(context = "EmailSummarizer", debug=DEBUG)


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


class Timezone(Enum):
    PST = "America/Los_Angeles" # Pacific Standard Time
    MST = "America/Denver" # Mountain Standard Time
    CST = "America/Chicago" # Central Standard Time
    EST = "America/New_York" # Eastern Standard Time
    UTC = "UTC" # Coordinated Universal Time

@dataclass
class EventTimeInfo():
    start_time : datetime    # If the email is for a time-bounded event, the start time of the event.
    end_time : datetime      # If the email is for a time-bounded event, the end time of the event. 
    timezone : Timezone = Timezone.PST  # The timezone of the event times. Default to PST if not specified.

@dataclass
class EmailSummaryResponseFormat:
    """ Summary for a single email.  """
    
    email : Email | None  # The email being summarized. Leave none if is_important is false.
    is_important: bool #Whether the email is important and should be included in the summary.
    event_time_info: EventTimeInfo | None  # If the email is about a time-bounded event, the event time info.


@dataclass 
class EmailSummaryResponseFormatDebug(EmailSummaryResponseFormat):
    """ Summary for a single email.  """
    justification: str  # Explanation for why the email was marked important or not.



CACHED_EMAIL_SUMMARIZER_SYSTEM_MESSAGE = SystemMessage(
    content=[
        {
            "type": "text",
            "text": SUMMARIZER_SYSTEM_PROMPT_TEMPLATE,
            "cache_control": {"type": "ephemeral"},  # 🔑 THIS enables caching
        }
    ]
)

def init_email_summarizer(model : BaseChatModel, with_critic: bool = False, response_format : type[EmailSummaryResponseFormat] = EmailSummaryResponseFormat) -> CompiledStateGraph:
    agent = _init_email_summarizer_agent(model, response_format=response_format)
    critic_agent = _init_critic_agent(model) if with_critic else None
    email_service = EmailService.create_email_service()
    return EmailSummarizer(agent, email_service, critic_agent= critic_agent)


def _init_email_summarizer_agent(model : BaseChatModel, response_format : type[EmailSummaryResponseFormat] = EmailSummaryResponseFormat) -> CompiledStateGraph:
    return create_agent(
        model=model,
        system_prompt = CACHED_EMAIL_SUMMARIZER_SYSTEM_MESSAGE,
        response_format=ToolStrategy(response_format),
    )

CACHED_CRITIC_SYSTEM_MESSAGE = SystemMessage(
    content=[
        {
            "type": "text",
            "text": CRITIC_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # 🔑 THIS enables caching
        }
    ]
)

def _create_default_event_time_info() -> EventTimeInfo:
    now = datetime.now(timezone.utc)
    return EventTimeInfo(
        start_time= now + timedelta(hours=1),
        end_time= now + timedelta(hours=2),
        timezone= Timezone.UTC
    )


def _init_critic_agent(model : BaseChatModel) -> CompiledStateGraph:
    return create_agent(
        model=model,
        system_prompt = CACHED_CRITIC_SYSTEM_MESSAGE,
        response_format=ToolStrategy(EmailSummaryResponseFormat),

    )




INVOKE_CONFIG=  {"configurable": {"max_tokens": 100}}

log = Logger(context = "EmailSummarizer", debug=DEBUG)

@logged_class
class EmailSummarizer:
    async def _invoke_with_exp_backoff_retries(self, call):
        for n in range(8): # max of up to 4 minutes
            try:
                return await call()
            except RateLimitError as e:
                #randomly wait between 2^n and 2^(n+1) seconds
                wait_time = random.uniform(2**n, 2**(n+1))
                log.log(f"Rate limit error encountered in attempt {n}. Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        raise Exception("Max retries exceeded due to rate limiting.")
    

    def __init__(self,  email_summarizer_agent : CompiledStateGraph,  email_service: EmailService, critic_agent : CompiledStateGraph | None = None):
        self.email_summarizer_agent = email_summarizer_agent
        self.email_service = email_service
        self.critic_agent = critic_agent

    async def _summarize_single_email_async(self, email: Email) -> EmailSummaryResponseFormat:
        email_str = strip_html_and_urls(str(email))[:MAX_CHARS_PER_EMAIL]
        logger.log("Summarizing Email with Subject: " + email.subject)

        resp = await self.email_summarizer_agent.ainvoke(
            {"messages": [{"role": "user", "content": email_str}]},
            config=INVOKE_CONFIG,
        )
        logger.log("Completed invocation for Email with Subject: " + email.subject)

        # log message history for debugging
        logger.log("LLM Message History:\n" + str(resp))

        # usage = resp.get("usage") or resp.get("llm_output", {}).get("usage")

        # # log token usage
        # logger.log(f"Token usage for summarizing email '{email.subject}': {usage}")

        structured : EmailSummaryResponseFormat = resp["structured_response"]

        # only invoke critic if email marked not important, to prevent false negatives
        if not structured.is_important and self.critic_agent:
            critic_resp = await self.critic_agent.ainvoke(
                {"messages": [{"role": "user", "content": str(structured)}]},
                config=INVOKE_CONFIG,
            )
            # usage = resp.get("usage") or resp.get("llm_output", {}).get("usage")
            # logger.log(f"Token usage for critic on email '{email.subject}': {usage}")
            structured = critic_resp["structured_response"]

        return structured
    
    async def _summarize_emails_async(self, emails: list[Email], concurrency: int = DEFAULT_CONCURRENCY):
        log.log(f"Summarizing {len(emails)} emails with concurrency {concurrency}...")
        sem = asyncio.Semaphore(concurrency) # limits how many tasks can actively make llm calls at once

        async def worker(idx: int, email: Email):
            log.log(f"Entering critical section for email {idx}, subject: {email.subject}")
            async with sem:
                try:
                    result = await asyncio.wait_for(
                        self._invoke_with_exp_backoff_retries(
                            lambda: self._summarize_single_email_async(email)
                        ),
                        timeout=TIMEOUTS_SECONDS,
                    )
                    return idx, result
                except asyncio.TimeoutError: # if it takes too long, mark as important by default and leave a note in body
                    log.log(f"TIMEOUT summarizing email {idx}")
                    email_copy = Email(
                        subject=f"Timeout for email : {email.subject}",
                        message_id=email.message_id,
                        body=email.body
                    )
                    
                    result = EmailSummaryResponseFormat(
                        email = email_copy,
                        is_important = True,
                        event_time_info = _create_default_event_time_info()
                    )
            log.log(f"Left critical section for email {idx}, subject: {email.subject}")
            return idx, result
        tasks = [asyncio.create_task(worker(i, e)) for i, e in enumerate(emails)]

        summaries = [None] * len(emails)
        done = 0
        for fut in asyncio.as_completed(tasks):
            idx, result = await fut

            result.email.message_id = emails[idx].message_id  # ensure message_id is set correctly
            summaries[idx] = result
            done += 1
            
            log.log(f"Progress: {done/len(emails)*100:.2f}%, ({done}/{len(emails)}) emails summarized.")
        log.log("Summarization complete.")
        return summaries

    def _summarize_emails(self, emails : list[Email]) -> list[EmailSummaryResponseFormat]:
        return asyncio.run(self._summarize_emails_async(emails))
    
    def summarize_last_n_emails(self, n=5):
        emails = list(self.email_service.get_last_n_emails(n=n))
        
        return self._summarize_emails(emails)
    

    
    def get_db(self):
        # returns the db used to track processed emails
        return self.email_db
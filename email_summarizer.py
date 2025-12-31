
import asyncio
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

MAX_CHARS_PER_EMAIL = 1000

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
SUMMARIZER_SYSTEM_PROMPT = "prompts/single_email_summarizer_system_prompt.txt"
CRITIC_SYSTEM_PROMPT = "prompts/critic_prompt.txt"
logger = Logger(context = "EmailSummarizer", debug=DEBUG)




@dataclass
class EmailSummaryResponseFormat:
    """ Summary for a single email.  """
    
    email : Email | None  # The email being summarized. Leave none if is_important is false.
    
    is_important: bool #Whether the email is important and should be included in the summary.

    justification: str  # Explanation for why the email was marked important or not.


CACHED_EMAIL_SUMMARIZER_SYSTEM_MESSAGE = SystemMessage(
    content=[
        {
            "type": "text",
            "text": SUMMARIZER_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # 🔑 THIS enables caching
        }
    ]
)


def _init_email_summarizer_agent(model : BaseChatModel) -> CompiledStateGraph:
    return create_agent(
        model=model,
        system_prompt = CACHED_EMAIL_SUMMARIZER_SYSTEM_MESSAGE,
        response_format=ToolStrategy(EmailSummaryResponseFormat),

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


def _init_critic_agent(model : BaseChatModel) -> CompiledStateGraph:
    return create_agent(
        model=model,
        system_prompt = CACHED_CRITIC_SYSTEM_MESSAGE,
        response_format=ToolStrategy(EmailSummaryResponseFormat),

    )


async def invoke_with_exp_backoff_retries(call):
    for n in range(8): # max of up to 4 minutes
        try:
            return await call()
        except RateLimitError as e:
            #randomly wait between 2^n and 2^(n+1) seconds
            wait_time = random.uniform(2**n, 2**(n+1))
            logger.log(f"Rate limit error encountered in attempt {n}. Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
    raise Exception("Max retries exceeded due to rate limiting.")

class EmailSummarizer:

    def __init__(self,  email_summarizer_agent : CompiledStateGraph,  email_service: EmailService, critic_agent : CompiledStateGraph | None = None):
        self.email_summarizer_agent = email_summarizer_agent
        self.email_service = email_service
        self.critic_agent = critic_agent

    async def _summarize_single_email_async(self, email: Email) -> EmailSummaryResponseFormat:
        email_str = strip_html_and_urls(str(email))[:MAX_CHARS_PER_EMAIL]
        logger.log("Summarizing Email:\n" + email_str)

        resp = await self.email_summarizer_agent.ainvoke(
            {"messages": [{"role": "user", "content": email_str}]},
            config={"configurable": {"max_tokens": 100}},
        )

        # usage = resp.get("usage") or resp.get("llm_output", {}).get("usage")

        # # log token usage
        # logger.log(f"Token usage for summarizing email '{email.subject}': {usage}")

        structured : EmailSummaryResponseFormat = resp["structured_response"]

        # only invoke critic if email marked not important, to prevent false negatives
        if not structured.is_important and self.critic_agent:
            critic_resp = await self.critic_agent.ainvoke(
                {"messages": [{"role": "user", "content": str(structured)}]},
                config={"configurable": {"max_tokens": 100}},
            )
            # usage = resp.get("usage") or resp.get("llm_output", {}).get("usage")
            # logger.log(f"Token usage for critic on email '{email.subject}': {usage}")
            structured = critic_resp["structured_response"]

        return structured
    
    async def _summarize_emails_async(self, emails: list[Email], concurrency: int = 10):
        sem = asyncio.Semaphore(concurrency) # limits how many tasks can actively make llm calls at once

        async def worker(idx: int, email: Email):
            async with sem:
                return idx, await invoke_with_exp_backoff_retries(lambda: self._summarize_single_email_async(email))

        tasks = [asyncio.create_task(worker(i, e)) for i, e in enumerate(emails)]

        summaries = [None] * len(emails)
        done = 0
        for fut in asyncio.as_completed(tasks):
            idx, result = await fut
            summaries[idx] = result
            done += 1
            if done % 5 == 0 or done == len(emails):
                print(f"Progress: {done/len(emails)*100:.2f}%")

        return summaries

    def _summarize_emails(self, emails : list[Email]) -> list[EmailSummaryResponseFormat]:
        return asyncio.run(self._summarize_emails_async(emails))
    
    def summarize_last_n_emails(self, n=5):
        emails = list(self.email_service.get_last_n_emails(n=n))
        
        return self._summarize_emails(emails)
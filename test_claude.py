from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from pprint import pprint
from constants import TIMEOUTS_SECONDS
checkpointer = InMemorySaver()

TEMPERATURE = 0 # Higher temperature means more creative/stochastic responses, lower means more deterministic (0 just takes max prob everytime)

@tool
def get_weather_for_location(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

@dataclass
class Context:
    """Custom runtime context schema."""
    user_id: str

# We use a dataclass here, but Pydantic models are also supported.
@dataclass
class ResponseFormat:
    """Response schema for the agent."""
    # A punny response (always required)
    punny_response: str
    # Any interesting information about the weather if available
    weather_conditions: str | None = None

@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Retrieve user information based on user ID."""
    user_id = runtime.context.user_id
    return "Florida" if user_id == "1" else "SF"



SYSTEM_PROMPT = """You are an expert weather forecaster, who speaks in puns.

You have access to two tools:

- get_weather_for_location: use this to get the weather for a specific location
- get_user_location: use this to get the user's location

If a user asks you for the weather, make sure you know the location. If you can tell from the question that they mean wherever they are, use the get_user_location tool to find their location."""

if __name__ == "__main__":

    model = init_chat_model(
        "claude-sonnet-4-5-20250929",
        temperature=TEMPERATURE,
        timeout=TIMEOUTS_SECONDS,
        max_tokens=1000
    )

    agent = create_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[get_user_location, get_weather_for_location],
        context_schema=Context,
        response_format=ToolStrategy(ResponseFormat),
        checkpointer=checkpointer
    )

    # `thread_id` is a unique identifier for a given conversation.
    config = {"configurable": {"thread_id": "1"}}

    response = agent.invoke(
        {"messages": [{"role": "user", "content": "what is the weather outside?"}]},
        config=config,
        context=Context(user_id="1")
    )

    pprint(response)#['structured_response'])

    # # Note that we can continue the conversation using the same `thread_id`.
    # response = agent.invoke(
    #     {"messages": [{"role": "user", "content": "thank you!"}]},
    #     config=config,
    #     context=Context(user_id="1")
    # )

    # pprint(response)#['structured_response'])
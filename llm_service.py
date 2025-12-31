from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Generator, Any
import os
from langchain_core.language_models.chat_models import BaseChatModel, BaseMessage, CallbackManagerForLLMRun, ChatResult, ChatResult

LOCAL_LLAMA_ENDPOINT = "http://localhost:11434"





class LLMService(ABC):

    @abstractmethod
    def generate_text_stream(self, prompt: str) -> Generator[str, None, None]:
        """Generates text from the given prompt as a stream."""
        pass

    def generate_text(self, prompt: str) -> str:
        return ''.join(list(self.generate_text_stream(prompt)))

LLAMA_3_1 = 'llama3.1:8b'
LLAMA_3_2_1B = 'llama3.2:1b'
from logger import logged_class
@logged_class
class LocalLlamaService(LLMService):
    """LLM Service using a local LLaMA model via REST API."""
    MODEL = LLAMA_3_2_1B
    def __init__(self, endpoint: str = LOCAL_LLAMA_ENDPOINT):
        self.endpoint = endpoint

    def generate_text_stream(self, prompt: str) -> Generator[str, None, None]:
        import requests
        import json

        payload = {
            "model": self.MODEL,
            "prompt": prompt,
            "stream": True
        }

        response = requests.post(os.path.join(self.endpoint, "api/generate"), json=payload, stream=True)

        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                yield data["response"]

from logger import logged_class
@logged_class
class LangchainAdapter(BaseChatModel):
    """Wrapper to use Langchain LLMs with our LLMService interface."""
    llm : LLMService

    def _llm_type(self) -> str:
        return "custom adapter wrapping LLMService"
    
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = "\n".join([msg.content for msg in messages])
        response_text_stream = self.llm.generate_text_stream(prompt)
        response_text = []

        for chunk in response_text_stream:
            response_text.append(chunk)
            
            # callback for new token
            if run_manager:
                run_manager.on_llm_new_token(chunk)

            if stop and any(s in chunk for s in stop):
                break # stop generation if any stop token is found

        return ChatResult(generations=[[{"text": ''.join(response_text)}]])
    
    # # async version
    # async def _agenerate(
    #     self,
    #     messages: list[BaseMessage],
    #     stop: list[str] | None = None,
    #     run_manager: CallbackManagerForLLMRun | None = None,
    #     **kwargs: Any,
    # ) -> ChatResult:
    #     # For simplicity, we call the synchronous version here.
    #     return self._generate(messages, stop, run_manager, **kwargs)
    
    #     def bind_tools(
    #     self,
    #     tools: Sequence[
    #         typing.Dict[str, Any] | type | Callable | BaseTool  # noqa: UP006
    #     ],
    #     *,
    #     tool_choice: str | None = None,
    #     **kwargs: Any,
    # ) -> Runnable[LanguageModelInput, AIMessage]:
    #     return create_tool_calling_runnable(
    #         self, tools, tool_choice=tool_choice, **kwargs
    #     )
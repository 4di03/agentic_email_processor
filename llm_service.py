from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Generator
import os
LOCAL_LLAMA_ENDPOINT = "http://localhost:11434"


class LLMService(ABC):

    @abstractmethod
    def generate_text_stream(self, prompt: str) -> Generator[str, None, None]:
        """Generates text from the given prompt as a stream."""
        pass

    def generate_text(self, prompt: str) -> str:
        return ''.join(list(self.generate_text_stream(prompt)))



class LocalLlamaService(LLMService):
    """LLM Service using a local LLaMA model via REST API."""
    MODEL = 'llama3.1:8b'
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


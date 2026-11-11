from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from northline_docs.prompts import SYSTEM_PROMPT, user_prompt


class ChatClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenAIChatClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return content or ""


class OpenAIGenerator:
    def __init__(self, client: ChatClient) -> None:
        self._client = client

    def generate(self, question: str, contexts: Sequence[str], version: str | None) -> str:
        return self._client.complete(SYSTEM_PROMPT, user_prompt(question, list(contexts), version))

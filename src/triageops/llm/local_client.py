"""Yerel LLM icin OpenAI uyumlu istemci sarmalayicisi.

Ollama, vLLM, LM Studio ve llama.cpp server gibi OpenAI uyumlu endpoint'lerin
hepsi `base_url` ayariyla calisir. Tool-calling (function calling) destegi
gerekir; onerilen modeller: Qwen2.5-Coder, Llama 3.3/3.1, Mistral, DeepSeek-Coder.
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from triageops.config import Settings, get_settings


class LocalLLM:
    def __init__(self, settings: Settings | None = None, client: Any | None = None):
        self.settings = settings or get_settings()
        self.client = client or OpenAI(
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key or "not-needed",
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
    ) -> Any:
        """Tek bir sohbet tamamlama cagrisi. Ham message nesnesini dondurur."""
        kwargs: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message

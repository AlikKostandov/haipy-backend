import json
import os
import random
import time
from typing import Any, Dict, List, Optional

from groq import Groq


class LLMError(Exception):
    pass


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty LLM response content")

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
        raise ValueError("LLM returned JSON but not an object")
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object boundaries found in LLM output")

    candidate = text[start : end + 1].strip()
    obj = json.loads(candidate)
    if not isinstance(obj, dict):
        raise ValueError("Extracted JSON is not an object")
    return obj


class LLMClient:
    def __init__(self, *, api_key: Optional[str] = None, timeout_s: float = 60, retries: int = 2):
        self.timeout_s = float(timeout_s)
        self.retries = int(retries)

        self.model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        self.debug = os.getenv("LLM_DEBUG", "false").lower() == "true"

        key = (api_key or os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY") or "").strip()
        if not key:
            raise LLMError("Missing Groq API key.")

        self.client = Groq(api_key=key, timeout=self.timeout_s, max_retries=0)

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        schema_name: str = "response",
        strict_schema: bool = True,
        temperature: float = 0.0,
        max_completion_tokens: int = 2048,
    ) -> Dict[str, Any]:
        json_rules = "You MUST output ONLY valid JSON. No prose. No markdown. No code fences. Return exactly one JSON object."

        if json_schema is not None:
            schema_hint = json.dumps(json_schema, ensure_ascii=False)
            strict_hint = "Strictly follow the schema." if strict_schema else "Follow the schema as a guideline."
            system_prompt = f"{json_rules}\n{strict_hint}\nSchemaName: {schema_name}\nSchema:\n{schema_hint}\n\n{system_prompt}"
        else:
            system_prompt = f"{json_rules}\n\n{system_prompt}"

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_err: Optional[Exception] = None

        for attempt in range(self.retries + 1):
            try:
                if self.debug:
                    print(f"[LLM] provider=groq model={self.model} attempt={attempt+1}/{self.retries+1}")

                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    top_p=1,
                    stream=False,
                    max_completion_tokens=max_completion_tokens,
                )

                content = (resp.choices[0].message.content or "").strip()
                return _extract_json_object(content)

            except Exception as e:
                last_err = e
                if self.debug:
                    print(f"[LLM] error: {type(e).__name__}: {e}")

                if attempt >= self.retries:
                    break

                base = 0.6 * (2 ** attempt)
                time.sleep(base + random.uniform(0.0, 0.25))

        raise LLMError(self._human_error(last_err)) from last_err

    def _human_error(self, err: Exception) -> str:
        msg = str(err).lower()

        if "invalid api key" in msg or "invalid_api_key" in msg:
            return "Неверный Groq API Key. Проверьте правильность ключа."

        if "rate limit" in msg or "429" in msg:
            return (
                "Превышен лимит запросов Groq API. "
                "Подождите немного или используйте другой ключ."
            )

        if "timeout" in msg:
            return "Превышено время ожидания ответа от модели. Попробуйте ещё раз."

        if "permission" in msg or "forbidden" in msg:
            return "Нет доступа к модели. Проверьте права вашего Groq API Key."

        return (
            "Не удалось получить ответ от модели. "
            "Проверьте ключ и попробуйте ещё раз."
        )

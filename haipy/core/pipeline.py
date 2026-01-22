from typing import Any, Dict

from .extract import build_llm_context
from .parsing import parse_notebook
from .prompts import USER_PROMPT_TEMPLATE, SYSTEM_PROMPT
from .schemas import EvaluationResponse
from .llm_client import LLMClient


def evaluate_notebook(ipynb_bytes: bytes, filename: str, llm: LLMClient) -> EvaluationResponse:
    cells = parse_notebook(ipynb_bytes)
    blocks_text = build_llm_context(cells)

    user_prompt = USER_PROMPT_TEMPLATE.format(filename=filename, blocks_text=blocks_text)

    raw: Dict[str, Any] = llm.generate_json(
        SYSTEM_PROMPT,
        user_prompt,
        json_schema=EvaluationResponse.model_json_schema(),
        schema_name="EvaluationResponse",
        strict_schema=True,
    )

    if isinstance(raw, dict):
        raw["filename"] = filename
        raw.setdefault("id", "run_demo")
        raw.setdefault("issues", [])
        raw.setdefault("feedback", [])

    return EvaluationResponse.model_validate(raw)

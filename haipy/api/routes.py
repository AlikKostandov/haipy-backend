from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from pydantic import ValidationError

from ..core.pipeline import evaluate_notebook
from ..core.llm_client import LLMClient, LLMError
from ..core.schemas import EvaluationResponse

router = APIRouter()


@router.post("/api/v1/evaluate-notebook", response_model=EvaluationResponse)
async def evaluate(
        file: UploadFile = File(...),
        x_groq_api_key: str = Header(default="", alias="X-Groq-Api-Key"),
):
    key = (x_groq_api_key or "").strip()
    if not key:
        raise HTTPException(status_code=401, detail="Missing Groq API key (X-Groq-Api-Key).")

    if not file.filename or not file.filename.endswith(".ipynb"):
        raise HTTPException(status_code=400, detail="Only .ipynb files are supported.")

    content = await file.read()
    try:
        llm = LLMClient(api_key=key)
        result = evaluate_notebook(content, file.filename, llm)
        return result
    except LLMError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=502, detail=f"LLM output validation failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {type(e).__name__}: {e}")

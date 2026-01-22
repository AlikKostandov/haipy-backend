from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import ValidationError

from ..core.pipeline import evaluate_notebook
from ..core.llm_client import LLMClient, LLMError
from ..core.schemas import EvaluationResponse

router = APIRouter()

@router.post("/api/v1/evaluate-notebook", response_model=EvaluationResponse)
async def evaluate(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".ipynb"):
        raise HTTPException(status_code=400, detail="Only .ipynb files are supported.")

    content = await file.read()
    try:
        llm = LLMClient()
        result = evaluate_notebook(content, file.filename, llm)
        return result
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=502, detail=f"LLM output validation failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {type(e).__name__}: {e}")

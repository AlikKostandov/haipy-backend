from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from typing import List

class Rubric(BaseModel):
    correctness: int = Field(ge=0, le=10)
    completeness: int = Field(ge=0, le=10)
    analysis_quality: int = Field(ge=0, le=10)
    structure: int = Field(ge=0, le=10)

    @property
    def total_points(self) -> int:
        return self.correctness + self.completeness + self.analysis_quality + self.structure

class EvaluationResponse(BaseModel):
    id: str = Field(default="run_demo")
    filename: str
    score_total: int = Field(ge=0, le=100, description="Overall score as percentage of max rubric points (40).")
    rubric: Rubric
    issues: List[str] = Field(default_factory=list)
    feedback: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _recompute_score_total(self) -> "EvaluationResponse":
        total = self.rubric.total_points
        self.score_total = int(round((total / 40) * 100))
        if self.score_total < 0:
            self.score_total = 0
        if self.score_total > 100:
            self.score_total = 100
        return self

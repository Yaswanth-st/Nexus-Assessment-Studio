from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator


class Skill(BaseModel):
    """Represents a skill with priority weight."""

    name: str = Field(..., min_length=1, description="Skill name")
    weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Priority weight (0.0-1.0)",
    )


class Question(BaseModel):
    """Represents a single question in the assessment."""

    type: Literal["MCQ", "SAQ", "True/False", "Coding"] = Field(
        ..., description="Question type"
    )
    skill: str = Field(..., description="Primary skill being tested")
    priority_rank: Optional[int] = Field(
        default=None, description="Skill priority rank (1=highest)"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(default="medium")
    question: str = Field(..., description="Question text")
    options: Optional[List[str]] = Field(default=None, description="Options for MCQ")
    answer: str = Field(..., description="Correct answer")


class AssessmentRequest(BaseModel):
    """Assessment generation request."""

    type: Literal["curriculum", "jd"] = Field(
        ..., description="Assessment source type"
    )
    skills: Optional[List[Skill]] = Field(
        default=None, description="Pre-defined skills (for curriculum mode)"
    )
    jd: Optional[str] = Field(default=None, description="Job description (for jd mode)")
    difficulty: Literal["easy", "medium", "hard"] = Field(default="medium")
    num_questions: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of questions (max 50)",
    )
    question_types: List[Literal["MCQ", "SAQ", "True/False", "Coding"]] = Field(
        default=["MCQ", "SAQ"],
        description="Types of questions to include",
    )

    @validator("num_questions")
    def validate_questions(cls, value: int) -> int:
        """Validate question count doesn't exceed the configured hard limit."""
        if value > 50:
            raise ValueError("Maximum 50 questions per generation")
        return value


class CoverageQuality(BaseModel):
    """Coverage quality metrics for a skill."""

    weight: float = Field(..., description="Skill priority weight")
    expected_questions: float = Field(..., description="Expected questions based on weight")
    actual_questions: int = Field(..., description="Actual questions generated")
    coverage_percentage: float = Field(
        ..., description="Percentage of assessment dedicated to skill"
    )
    aligned: bool = Field(..., description="Whether coverage aligns with prioritization")


class ValidationReport(BaseModel):
    """Assessment validation report."""

    total_questions: int = Field(..., description="Total questions generated")
    max_questions_limit: int = Field(default=50, description="Maximum question limit")
    total_skills: int = Field(..., description="Total number of skills")
    skills_covered: int = Field(..., description="Number of skills with questions")
    coverage: Dict[str, int] = Field(..., description="Question count per skill")
    coverage_quality: Dict[str, CoverageQuality] = Field(
        ..., description="Detailed quality metrics per skill"
    )
    all_skills_covered: bool = Field(
        ..., description="Whether all skills have at least one question"
    )
    priority_aligned: bool = Field(
        ..., description="Whether distribution aligns with skill priorities"
    )


class AssessmentResponse(BaseModel):
    """Complete assessment response."""

    assessment: List[Question] = Field(..., description="Generated questions")
    report: ValidationReport = Field(..., description="Validation report")
    metadata: Dict = Field(..., description="Generation metadata")

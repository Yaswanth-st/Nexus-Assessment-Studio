from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class Achievement(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    xp_value: int
    condition: str  # e.g., "first_correct", "5_streak", "100_percent_skill"


class SkillMastery(BaseModel):
    skill_name: str
    total_attempts: int
    correct_answers: int
    mastery_percentage: float  # 0-100
    mastery_level: str  # "novice", "intermediate", "advanced", "expert"
    xp_earned: int


class StreakData(BaseModel):
    current_streak: int
    max_streak: int
    streak_skill: Optional[str]
    last_correct_timestamp: Optional[datetime]


class UserProgress(BaseModel):
    session_id: str
    total_xp: int
    current_level: int
    total_questions_attempted: int
    total_correct: int
    accuracy_percentage: float
    current_streak: int
    max_streak: int
    achievements_unlocked: List[str]
    skill_mastery: List[SkillMastery]
    daily_xp: int
    daily_challenge_completed: bool
    behavioral_level: str  # "beginner", "intermediate", "advanced"


class QuestionAttempt(BaseModel):
    question_id: str
    skill: str
    user_answer: str
    is_correct: bool
    hints_used: int
    time_taken_seconds: int
    xp_earned: int
    streak_bonus: int
    achievements_unlocked: List[str]
    answer_revealed: bool


class HintResponse(BaseModel):
    hint: str
    hints_remaining: int
    total_hints_for_question: int
    can_reveal: bool  # True after 3 hints


class AnswerValidationResponse(BaseModel):
    is_correct: bool
    feedback: str
    xp_earned: int
    streak_bonus: int
    achievements_unlocked: List[str]
    hint_available: bool
    hints_used: int
    total_hints: int


class BehavioralSignal(BaseModel):
    signal_type: str  # "struggling", "rushing", "pattern_weakness", "momentum", "fatigue"
    skill: Optional[str]
    recommendation: str
    intervention_level: str  # "info", "warning", "urgent"
    suggested_action: Optional[str]

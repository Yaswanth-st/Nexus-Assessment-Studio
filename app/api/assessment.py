import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from app.services.assessment_service import generate_assessment
from app.services.document_parser import (
    extract_text_from_upload,
    extract_text_with_details_from_upload,
)
from app.services.curriculum_organizer import (
    analyze_curriculum_text,
    compose_curriculum_from_sections,
)
from app.services.gamification_service import gamification_engine
from app.services.hint_service import HintGenerator

router = APIRouter()


# Request/Response Models
class StartSessionRequest(BaseModel):
    user_id: str = None  # Optional, will generate if not provided


class AnswerAttemptRequest(BaseModel):
    session_id: str = None
    question_id: str
    question: dict = {}  # Full question object for hint generation
    user_answer: str
    time_taken_seconds: int = 0


class HintRequest(BaseModel):
    session_id: str = None
    question_id: str
    question: dict = {}


class RevealAnswerRequest(BaseModel):
    session_id: str = None
    question_id: str
    question: dict = {}


def _skills_from_text(text: str):
    """
    Parse explicit weighted lines only, e.g.:
    Python:0.4
    SQL:0.3
    APIs:0.3

    If not present, caller should use AI curriculum analysis from raw text.
    """
    lines = [line.strip(" -\t\r\n") for line in re.split(r"[\n]+", text) if line.strip()]
    parsed = []

    for line in lines:
        match = re.match(r"^(.+?)\s*:\s*([0-9]*\.?[0-9]+)\s*$", line)
        if not match:
            continue

        name = match.group(1).strip()
        weight = max(float(match.group(2)), 0.0)
        if name:
            parsed.append({"name": name, "weight": weight})

    if len(parsed) < 2:
        return []

    total = sum(item["weight"] for item in parsed)
    if total <= 0:
        equal = round(1.0 / len(parsed), 4)
        return [{"name": item["name"], "weight": equal} for item in parsed]

    return [
        {"name": item["name"], "weight": round(item["weight"] / total, 4)}
        for item in parsed
    ]


def _parse_selected_sections(selected_sections: str):
    if not selected_sections:
        return []
    return [part.strip() for part in selected_sections.split(",") if part.strip()]

@router.post("/generate")
async def generate(payload: dict):
    return await generate_assessment(payload)


@router.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    try:
        text, details = await extract_text_with_details_from_upload(file)
        return {
            "filename": file.filename,
            "text": text,
            "extraction_method": details.get("method", "native"),
            "file_extension": details.get("extension"),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to parse document") from exc


@router.post("/curriculum/options")
async def curriculum_options(payload: dict):
    try:
        text = str(payload.get("curriculum_text", "") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="curriculum_text is required")

        analysis = analyze_curriculum_text(text)
        return {
            "curriculum_text": text,
            "overview": analysis.get("overview", {}),
            "sections": analysis.get("sections", []),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to analyze curriculum") from exc


@router.post("/curriculum/options-from-document")
async def curriculum_options_from_document(file: UploadFile = File(...)):
    try:
        text, extraction_details = await extract_text_with_details_from_upload(file)
        analysis = analyze_curriculum_text(text)
        return {
            "filename": file.filename,
            "curriculum_text": text,
            "overview": analysis.get("overview", {}),
            "sections": analysis.get("sections", []),
            "extraction_method": extraction_details.get("method", "native"),
            "file_extension": extraction_details.get("extension"),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze curriculum document",
        ) from exc


@router.post("/generate-from-document")
async def generate_from_document(
    file: UploadFile = File(...),
    input_type: str = Form("jd"),
    difficulty: str = Form("medium"),
    num_questions: int = Form(10),
    question_types: str = Form("MCQ,SAQ"),
    selected_sections: str = Form(""),
):
    try:
        text, extraction_details = await extract_text_with_details_from_upload(file)
        selected_section_ids = _parse_selected_sections(selected_sections)

        if input_type == "curriculum":
            curriculum_analysis = analyze_curriculum_text(text)
            scoped_text = compose_curriculum_from_sections(
                curriculum_analysis.get("sections", []),
                selected_section_ids,
            )

            # First try explicit skill line parsing, then AI curriculum analysis fallback.
            skills = _skills_from_text(scoped_text)
            payload = {
                "type": "curriculum",
                "difficulty": difficulty,
                "num_questions": num_questions,
                "question_types": _parse_question_types(question_types),
            }
            if skills:
                payload["skills"] = skills
            else:
                payload["curriculum_text"] = scoped_text
        else:
            payload = {
                "type": "jd",
                "jd": text,
                "difficulty": difficulty,
                "num_questions": num_questions,
                "question_types": _parse_question_types(question_types),
            }

        result = await generate_assessment(payload)
        result["metadata"] = {
            **result.get("metadata", {}),
            "source": "document",
            "filename": file.filename,
            "input_type": input_type,
            "extraction_method": extraction_details.get("method", "native"),
            "file_extension": extraction_details.get("extension"),
            "selected_sections": selected_section_ids,
        }
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate assessment from document",
        ) from exc


# ==================== ENGAGEMENT ENGINE ENDPOINTS ====================


@router.post("/session/start")
async def start_session(request: StartSessionRequest | None = None):
    """Initialize a new assessment session with gamification tracking"""
    try:
        session_id = (request.user_id if request else None) or str(uuid.uuid4())
        session = gamification_engine.create_session(session_id)
        return {
            "session_id": session_id,
            "status": "active",
            "message": f"Assessment session created. Ready to test your skills! 🚀",
            "initial_state": {
                "total_xp": 0,
                "current_level": 1,
                "current_streak": 0,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/session/{session_id}/answer")
async def submit_answer(session_id: str, request: dict = Body(default_factory=dict)):
    """Submit an answer and get XP, streak, achievement feedback"""
    try:
        request = request or {}
        session = gamification_engine.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Validate answer
        question = request.get("question") or {}
        if not question:
            raise HTTPException(status_code=400, detail="Question payload is required")
        correct_answer = question.get("answer", "")
        user_answer = str(request.get("user_answer", "") or "").strip()
        if not user_answer:
            raise HTTPException(status_code=400, detail="User answer is required")
        is_correct = HintGenerator.validate_answer(
            user_answer, correct_answer, answer_type="fuzzy"
        )

        # Track hints used (from session state if available)
        hints_used = question.get("_hints_used", 0)

        # Update progress and get rewards
        progress = gamification_engine.update_progress(
            session_id=session_id,
            skill=question.get("skill", "Unknown"),
            is_correct=is_correct,
            hints_used=hints_used,
            time_taken_seconds=int(request.get("time_taken_seconds", 0) or 0),
            user_answer=user_answer,
            correct_answer=correct_answer,
        )

        # Get feedback message
        feedback = HintGenerator.get_feedback(
            user_answer, correct_answer, is_correct, hints_used
        )

        # Get behavioral signals
        signals = gamification_engine.get_behavioral_signals(session_id)

        return {
            "is_correct": is_correct,
            "feedback": feedback,
            "correct_answer": correct_answer if not is_correct else None,
            "xp_earned": progress.get("xp_earned", 0),
            "streak_bonus": progress.get("streak_bonus", 0),
            "achievements_unlocked": progress.get("achievements_unlocked", []),
            "current_streak": progress.get("current_streak", 0),
            "total_xp": progress.get("total_xp", 0),
            "current_level": progress.get("current_level", 1),
            "behavioral_signals": signals,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/session/{session_id}/hint")
async def get_hint(session_id: str, request: dict = Body(default_factory=dict)):
    """Get next progressive hint for a question"""
    try:
        request = request or {}
        session = gamification_engine.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        question = request.get("question") or {}
        if not question:
            raise HTTPException(status_code=400, detail="Question payload is required")
        hints_used = question.get("_hints_used", 0)

        # Check if all hints have been used
        if hints_used >= 3:
            return {
                "error": "All hints used",
                "message": "No more hints available. You can reveal the answer now.",
                "can_reveal": True,
                "hints_used": hints_used,
                "total_hints": 3,
            }

        # Generate hint based on level
        hint_1, hint_2, hint_3 = HintGenerator.generate_hints(question, question.get("difficulty", "medium"))
        hints = [hint_1, hint_2, hint_3]
        
        current_hint = hints[hints_used]

        return {
            "hint": current_hint,
            "hint_level": hints_used + 1,
            "hints_used": hints_used + 1,
            "total_hints": 3,
            "can_reveal": hints_used >= 2,  # Can reveal after 3rd hint
            "message": "💡 Here's your hint. Take time to think it through!" if hints_used < 2 else "One more hint available, or you can reveal the answer.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/session/{session_id}/reveal")
async def reveal_answer(session_id: str, request: dict = Body(default_factory=dict)):
    """Reveal answer after using all hints or on request"""
    try:
        request = request or {}
        session = gamification_engine.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        question = request.get("question") or {}
        if not question:
            raise HTTPException(status_code=400, detail="Question payload is required")
        correct_answer = question.get("answer", "")
        hints_used = question.get("_hints_used", 0)

        # Log the reveal (no XP penalty, but it's noted)
        return {
            "answer": correct_answer,
            "explanation": f"The correct answer is: **{correct_answer}**\n\nThis demonstrates {question.get('skill', 'this concept')}.",
            "hints_were_used": hints_used,
            "xp_penalty": 0 if hints_used >= 3 else 0,
            "message": "📖 Answer revealed. Move on to the next question to keep building your streak!",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/session/{session_id}/progress")
async def get_progress(session_id: str):
    """Get comprehensive user progress and stats"""
    try:
        progress = gamification_engine.get_user_progress(session_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Session not found")

        return progress
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/session/{session_id}/signals")
async def get_signals(session_id: str):
    """Get behavioral signals and intervention recommendations"""
    try:
        signals = gamification_engine.get_behavioral_signals(session_id)
        return {
            "signals": signals,
            "count": len(signals),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
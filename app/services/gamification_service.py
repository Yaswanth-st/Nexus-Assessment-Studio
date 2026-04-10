"""
Gamification Engine - Core engagement system with meaningful progression
"""
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from app.schemas.gamification_schema import Achievement, BehavioralSignal, SkillMastery


# XP Constants
BASE_XP_FOR_CORRECT = 100
FIRST_TRY_BONUS = 25
SECOND_TRY_BONUS = 15
THIRD_TRY_BONUS = 5
REVEAL_ANSWER_XP = 50
HINT_COST = 10

# Streak Bonuses
STREAK_3_BONUS = 50
STREAK_5_BONUS = 100
STREAK_10_BONUS = 250

# Achievements Database
ACHIEVEMENTS = {
    "first_correct": Achievement(
        id="first_correct",
        name="First Blood 🎯",
        description="Get your first question correct",
        icon="🎯",
        xp_value=10,
        condition="first_correct"
    ),
    "streak_3": Achievement(
        id="streak_3",
        name="On a Roll 🔥",
        description="Get 3 consecutive questions correct",
        icon="🔥",
        xp_value=50,
        condition="streak_3"
    ),
    "streak_5": Achievement(
        id="streak_5",
        name="Unstoppable ⚡",
        description="Get 5 consecutive questions correct",
        icon="⚡",
        xp_value=100,
        condition="streak_5"
    ),
    "streak_10": Achievement(
        id="streak_10",
        name="Legendary 👑",
        description="Get 10 consecutive questions correct",
        icon="👑",
        xp_value=250,
        condition="streak_10"
    ),
    "speed_demon": Achievement(
        id="speed_demon",
        name="Speed Demon ⚙️",
        description="Answer 5 questions in under 30 seconds each",
        icon="⚙️",
        xp_value=75,
        condition="speed_demon"
    ),
    "skill_master": Achievement(
        id="skill_master",
        name="Skill Master 🏆",
        description="Achieve 100% accuracy on any skill (5+ questions)",
        icon="🏆",
        xp_value=150,
        condition="skill_master"
    ),
    "persistence": Achievement(
        id="persistence",
        name="Persistence Pays 💪",
        description="Get a question correct after using all 3 hints",
        icon="💪",
        xp_value=75,
        condition="persistence"
    ),
    "perfect_streak": Achievement(
        id="perfect_streak",
        name="Perfect Storm 🌪️",
        description="Answer 5+ questions without using hints",
        icon="🌪️",
        xp_value=125,
        condition="perfect_streak"
    ),
    "comeback_king": Achievement(
        id="comeback_king",
        name="Comeback King 🎭",
        description="Get 3 consecutive questions correct after a wrong answer",
        icon="🎭",
        xp_value=100,
        condition="comeback_king"
    ),
    "hint_hider": Achievement(
        id="hint_hider",
        name="Self-Reliant 🚀",
        description="Complete 10 questions without using any hints",
        icon="🚀",
        xp_value=100,
        condition="hint_hider"
    ),
}


class Achievement:
    def __init__(self, id, name, description, icon, xp_value, condition):
        self.id = id
        self.name = name
        self.description = description
        self.icon = icon
        self.xp_value = xp_value
        self.condition = condition


class GamificationEngine:
    """Manages XP, streaks, achievements, and behavioral engagement"""

    def __init__(self):
        self.sessions_file = "sessions.json"
        self.load_sessions()

    def load_sessions(self):
        """Load all user sessions from disk"""
        if os.path.exists(self.sessions_file):
            with open(self.sessions_file, "r") as f:
                self.sessions = json.load(f)
        else:
            self.sessions = {}

    def save_sessions(self):
        """Persist sessions to disk"""
        with open(self.sessions_file, "w") as f:
            json.dump(self.sessions, f, indent=2)

    def create_session(self, session_id: str) -> Dict:
        """Initialize a new user session"""
        session = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "total_xp": 0,
            "current_level": 1,
            "total_questions": 0,
            "correct_answers": 0,
            "current_streak": 0,
            "max_streak": 0,
            "achievements": [],
            "skill_stats": {},  # {skill: {attempts, correct, xp}}
            "question_history": [],  # Track each attempt
            "daily_xp": 0,
            "daily_challenge_completed": False,
            "last_activity": datetime.now().isoformat(),
            "consecutive_correct_without_hints": 0,
            "last_wrong_timestamp": None,
            "struggling_skills": [],  # Skills where user got 3+ wrong
        }
        self.sessions[session_id] = session
        self.save_sessions()
        return session

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Retrieve user session"""
        return self.sessions.get(session_id)

    def calculate_xp(
        self,
        is_correct: bool,
        hints_used: int,
        time_taken_seconds: int,
        current_streak: int,
    ) -> Tuple[int, List[str], int]:
        """
        Calculate XP earned and check achievements.
        Returns: (xp_earned, achievements_unlocked, streak_bonus)
        """
        xp = 0
        achievements = []
        streak_bonus = 0

        if not is_correct:
            return 0, [], 0

        # Base XP for correct answer
        xp = BASE_XP_FOR_CORRECT

        # Attempt bonus (less hints = more XP)
        if hints_used == 0:
            xp += FIRST_TRY_BONUS
        elif hints_used == 1:
            xp += SECOND_TRY_BONUS
        elif hints_used == 2:
            xp += THIRD_TRY_BONUS
        elif hints_used == 3:
            # After all hints revealed, only base XP
            xp = REVEAL_ANSWER_XP

        # Speed bonus (under 30 seconds)
        if time_taken_seconds < 30:
            xp += 15

        # Streak bonuses
        if (current_streak + 1) == 3:
            streak_bonus = STREAK_3_BONUS
            xp += streak_bonus
        elif (current_streak + 1) == 5:
            streak_bonus = STREAK_5_BONUS
            xp += streak_bonus
            if "streak_5" not in achievements:
                achievements.append("streak_5")
        elif (current_streak + 1) == 10:
            streak_bonus = STREAK_10_BONUS
            xp += streak_bonus
            if "streak_10" not in achievements:
                achievements.append("streak_10")

        return xp, achievements, streak_bonus

    def update_progress(
        self,
        session_id: str,
        skill: str,
        is_correct: bool,
        hints_used: int,
        time_taken_seconds: int,
        user_answer: str,
        correct_answer: str,
    ) -> Dict:
        """Update session progress after each attempt"""
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)

        # Calculate XP and achievements
        xp_earned, newly_unlocked = self._calculate_xp_and_achievements(
            session, is_correct, hints_used, time_taken_seconds, skill, correct_answer
        )

        # Update streaks
        if is_correct:
            session["current_streak"] += 1
            if session["current_streak"] > session["max_streak"]:
                session["max_streak"] = session["current_streak"]
            session["consecutive_correct_without_hints"] += (
                1 if hints_used == 0 else 0
            )
        else:
            session["current_streak"] = 0
            session["consecutive_correct_without_hints"] = 0
            session["last_wrong_timestamp"] = datetime.now().isoformat()

        # Update skill stats
        if skill not in session["skill_stats"]:
            session["skill_stats"][skill] = {
                "attempts": 0,
                "correct": 0,
                "xp": 0,
                "wrong_count": 0,
            }

        session["skill_stats"][skill]["attempts"] += 1
        if is_correct:
            session["skill_stats"][skill]["correct"] += 1
        else:
            session["skill_stats"][skill]["wrong_count"] += 1

        session["skill_stats"][skill]["xp"] += xp_earned

        # Track question history
        session["question_history"].append(
            {
                "skill": skill,
                "is_correct": is_correct,
                "hints_used": hints_used,
                "time_taken": time_taken_seconds,
                "xp_earned": xp_earned,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Update totals
        session["total_questions"] += 1
        session["total_xp"] += xp_earned
        session["daily_xp"] += xp_earned
        if is_correct:
            session["correct_answers"] += 1

        # Update level (every 500 XP = 1 level)
        session["current_level"] = max(1, session["total_xp"] // 500 + 1)

        # Update last activity
        session["last_activity"] = datetime.now().isoformat()

        # Add to achievements if not already there
        for ach in newly_unlocked:
            if ach not in session["achievements"]:
                session["achievements"].append(ach)

        self.save_sessions()

        return {
            "xp_earned": xp_earned,
            "achievements_unlocked": newly_unlocked,
            "current_streak": session["current_streak"],
            "total_xp": session["total_xp"],
            "current_level": session["current_level"],
        }

    def _calculate_xp_and_achievements(
        self,
        session: Dict,
        is_correct: bool,
        hints_used: int,
        time_taken_seconds: int,
        skill: str,
        correct_answer: str,
    ) -> Tuple[int, List[str]]:
        """Internal method to calculate XP and unlock achievements"""
        xp = 0
        achievements = []

        if not is_correct:
            return 0, []

        # Base XP
        xp = BASE_XP_FOR_CORRECT

        # Attempt bonuses
        if hints_used == 0:
            xp += FIRST_TRY_BONUS
        elif hints_used == 1:
            xp += SECOND_TRY_BONUS
        elif hints_used == 2:
            xp += THIRD_TRY_BONUS
        else:
            xp = REVEAL_ANSWER_XP

        # Speed bonus
        if time_taken_seconds < 30:
            xp += 15
            if session["consecutive_correct_without_hints"] >= 4:
                if "speed_demon" not in session["achievements"]:
                    achievements.append("speed_demon")

        # Streak bonuses
        new_streak = session["current_streak"] + 1
        if new_streak == 3:
            xp += STREAK_3_BONUS
        elif new_streak == 5:
            xp += STREAK_5_BONUS
            if "streak_5" not in session["achievements"]:
                achievements.append("streak_5")
        elif new_streak == 10:
            xp += STREAK_10_BONUS
            if "streak_10" not in session["achievements"]:
                achievements.append("streak_10")

        # First correct
        if session["total_questions"] == 0:
            if "first_correct" not in session["achievements"]:
                achievements.append("first_correct")

        # Skill master (100% on 5+ questions)
        if skill in session["skill_stats"]:
            stat = session["skill_stats"][skill]
            if (
                stat["attempts"] >= 5
                and stat["correct"] == stat["attempts"]
                and "skill_master" not in session["achievements"]
            ):
                achievements.append("skill_master")
                xp += 50

        # Persistence (correct after 3 hints)
        if hints_used == 3:
            if "persistence" not in session["achievements"]:
                achievements.append("persistence")
                xp += 25

        # Self-reliant (10 without hints)
        if session["consecutive_correct_without_hints"] >= 10:
            if "hint_hider" not in session["achievements"]:
                achievements.append("hint_hider")
                xp += 50

        return xp, achievements

    def get_hint_for_question(
        self, session_id: str, question: Dict, hint_count: int
    ) -> str:
        """Generate contextual hints based on question and user level"""
        skill = question.get("skill", "").lower()
        question_text = question.get("question", "")
        options = question.get("options", [])
        answer = question.get("answer", "")

        hints = [
            self._generate_hint_level_1(question, skill),
            self._generate_hint_level_2(question, skill, options, answer),
            self._generate_hint_level_3(question, skill, options, answer),
        ]

        return hints[min(hint_count, 2)] if hint_count < len(hints) else hints[-1]

    def _generate_hint_level_1(self, question: Dict, skill: str) -> str:
        """First hint: General direction"""
        question_text = question.get("question", "")
        skill_hints = {
            "python": "Think about Python's syntax and naming conventions.",
            "sql": "Consider the table structure and relationships involved.",
            "system design": "Focus on scalability, reliability, and maintainability.",
            "api design": "Think about REST principles and HTTP methods.",
            "database": "Consider indexing, query optimization, and data structure.",
            "testing": "Think about coverage, edge cases, and test patterns.",
        }

        return skill_hints.get(
            skill, "Read the question carefully. What is it really asking for?"
        )

    def _generate_hint_level_2(
        self, question: Dict, skill: str, options: List, answer: str
    ) -> str:
        """Second hint: Eliminate wrong approaches"""
        if options and len(options) > 0:
            wrong_options = [opt for opt in options if opt != answer]
            if wrong_options:
                return f"The answer is NOT about {wrong_options[0].lower()}. Think about what the question is fundamentally asking."

        return "Reconsider your approach. What's the core principle or best practice here?"

    def _generate_hint_level_3(
        self, question: Dict, skill: str, options: List, answer: str
    ) -> str:
        """Third hint: Almost there (without revealing)"""
        if options and len(options) > 0:
            correct_start = answer[:2] if len(answer) > 1 else answer[0]
            return f"The answer starts with '{correct_start}...' or contains that concept. Do you see it in the options?"

        return f"The answer is related to: {ACHIEVEMENTS[skill].name if skill in [a for a in ACHIEVEMENTS] else 'best practices'}. Look for that concept."

    def get_behavioral_signals(
        self, session_id: str
    ) -> List[Dict]:
        """Detect behavioral patterns and suggest intervention"""
        session = self.get_session(session_id)
        if not session:
            return []

        signals = []

        # Struggling detection (3+ wrong on same skill)
        for skill, stats in session["skill_stats"].items():
            if stats["wrong_count"] >= 3:
                accuracy = stats["correct"] / stats["attempts"] * 100
                if accuracy < 50:
                    signals.append(
                        {
                            "type": "struggling",
                            "skill": skill,
                            "message": f"📉 You're having trouble with {skill.title()}. Want to review the fundamentals?",
                            "recommendation": f"Try our {skill.title()} fundamentals challenge",
                            "urgency": "warning",
                        }
                    )

        # Fatigue detection (too many questions / low accuracy recently)
        recent_questions = session["question_history"][-5:] if session["question_history"] else []
        if len(recent_questions) >= 3:
            recent_correct = sum(1 for q in recent_questions if q["is_correct"])
            if recent_correct < len(recent_questions) * 0.4:
                signals.append(
                    {
                        "type": "fatigue",
                        "message": "😴 Your answers are slowing down. Take a 5-minute break!",
                        "recommendation": "Comeback stronger in a few minutes",
                        "urgency": "info",
                    }
                )

        # Momentum detection (on a winning streak)
        if session["current_streak"] >= 3:
            signals.append(
                {
                    "type": "momentum",
                    "message": f"🔥 You're on a {session['current_streak']}-question streak! Keep it up!",
                    "recommendation": "Keep pushing, you're doing great",
                    "urgency": "info",
                }
            )

        # Time pressure detection
        if session["question_history"]:
            avg_time = sum(q["time_taken"] for q in session["question_history"][-5:]) / len(session["question_history"][-5:])
            if avg_time < 15:
                signals.append(
                    {
                        "type": "rushing",
                        "message": "⚡ Slow down! You're answering too fast.",
                        "recommendation": "Take more time to think through answers",
                        "urgency": "warning",
                    }
                )

        return signals

    def get_user_progress(self, session_id: str) -> Dict:
        """Get comprehensive user progress report"""
        session = self.get_session(session_id)
        if not session:
            return {}

        accuracy = (
            session["correct_answers"] / session["total_questions"] * 100
            if session["total_questions"] > 0
            else 0
        )

        skill_mastery = []
        for skill, stats in session["skill_stats"].items():
            mastery_pct = (
                stats["correct"] / stats["attempts"] * 100
                if stats["attempts"] > 0
                else 0
            )
            if mastery_pct < 50:
                level = "novice"
            elif mastery_pct < 75:
                level = "intermediate"
            elif mastery_pct < 90:
                level = "advanced"
            else:
                level = "expert"

            skill_mastery.append(
                {
                    "skill": skill,
                    "accuracy": round(mastery_pct, 1),
                    "level": level,
                    "attempts": stats["attempts"],
                    "correct": stats["correct"],
                    "xp": stats["xp"],
                }
            )

        return {
            "session_id": session_id,
            "total_xp": session["total_xp"],
            "current_level": session["current_level"],
            "total_questions": session["total_questions"],
            "correct_answers": session["correct_answers"],
            "accuracy": round(accuracy, 1),
            "current_streak": session["current_streak"],
            "max_streak": session["max_streak"],
            "achievements": session["achievements"],
            "skill_mastery": skill_mastery,
            "daily_xp": session["daily_xp"],
            "created_at": session["created_at"],
        }


# Global instance
gamification_engine = GamificationEngine()

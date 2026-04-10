"""
Intelligent Hint Generation System
Provides progressive hints without revealing answers
"""
from typing import Dict, List, Tuple


class HintGenerator:
    """Generates smart, progressive hints for different question types"""

    @staticmethod
    def generate_hints(question: Dict, difficulty: str) -> Tuple[str, str, str]:
        """
        Generate 3 progressive hints for a question.
        Level 1: General direction
        Level 2: Eliminate wrong approaches
        Level 3: Nearly there (without spoiling)
        Returns: (hint_1, hint_2, hint_3)
        """
        q_type = question.get("type", "MCQ").upper()
        skill = question.get("skill", "").lower()
        question_text = question.get("question", "")
        answer = question.get("answer", "")
        options = question.get("options", [])

        if q_type == "MCQ":
            return HintGenerator._mcq_hints(skill, question_text, options, answer)
        elif q_type == "SAQ":
            return HintGenerator._saq_hints(skill, question_text, answer, difficulty)
        elif q_type == "CODING":
            return HintGenerator._coding_hints(skill, question_text, answer)
        else:
            return HintGenerator._generic_hints(skill, question_text, answer)

    @staticmethod
    def _mcq_hints(
        skill: str, question_text: str, options: List, answer: str
    ) -> Tuple[str, str, str]:
        """Hints for multiple choice questions"""
        hint_1 = HintGenerator._get_skill_hint_level_1(skill)

        # Hint 2: Eliminate a wrong option
        wrong_options = [opt for opt in options if opt != answer]
        if len(wrong_options) >= 2:
            hint_2 = f"✗ Option '{wrong_options[0][:30]}...' is a common trap. Think about why that's not ideal."
        elif wrong_options:
            hint_2 = f"✗ '{wrong_options[0]}' is incorrect. The answer is something different."
        else:
            hint_2 = "Look at the options closely. Which one aligns with best practices?"

        # Hint 3: Point to right answer without fully revealing
        if options:
            answer_idx = None
            for idx, opt in enumerate(options):
                if opt == answer:
                    answer_idx = idx
                    break

            if answer_idx is not None:
                hints_3_options = ["A", "B", "C", "D"]
                if answer_idx < len(hints_3_options):
                    hint_3 = f"💡 The answer is **(option {hints_3_options[answer_idx].upper()})** - look for the concept related to {answer[:20]}..."
                else:
                    hint_3 = f"💡 The answer starts with '{answer[0].upper()}'. Which option matches that?"
            else:
                hint_3 = f"💡 Look for '{answer[:15]}' in the options"
        else:
            hint_3 = "💡 You're very close. Check if your reasoning aligns with real-world best practices."

        return hint_1, hint_2, hint_3

    @staticmethod
    def _saq_hints(
        skill: str, question_text: str, answer: str, difficulty: str
    ) -> Tuple[str, str, str]:
        """Hints for short answer questions"""
        hint_1 = HintGenerator._get_skill_hint_level_1(skill)

        # Hint 2: Approach/methodology
        hint_2 = HintGenerator._get_approach_hint(skill, difficulty)

        # Hint 3: Key concept
        answer_keywords = answer.split()[:3] if answer else []
        keywords_str = ", ".join(answer_keywords)
        hint_3 = f"💡 The answer involves: **{keywords_str}**. Build your response around these concepts."

        return hint_1, hint_2, hint_3

    @staticmethod
    def _coding_hints(
        skill: str, question_text: str, answer: str
    ) -> Tuple[str, str, str]:
        """Hints for coding challenges"""
        hint_1 = "🔍 Look at the problem requirements. What data structure or algorithm would be most efficient?"

        # Hint 2: Algorithm/approach
        if "sort" in question_text.lower():
            hint_2 = "💭 Think about sorting algorithms. Consider time and space complexity."
        elif "search" in question_text.lower():
            hint_2 = "💭 Should you iterate, binary search, or use a hash map for faster lookup?"
        elif "tree" in question_text.lower() or "graph" in question_text.lower():
            hint_2 = "💭 Consider DFS or BFS approaches. What's the traversal order needed?"
        elif "dynamic" in question_text.lower():
            hint_2 = "💭 Think about subproblems. Can you break this into smaller pieces?"
        else:
            hint_2 = "💭 What's the key insight? Break the problem into smaller parts."

        # Hint 3: Code structure
        hint_3 = "💡 Look at the solution structure. Start with the main logic, then optimize."

        return hint_1, hint_2, hint_3

    @staticmethod
    def _generic_hints(
        skill: str, question_text: str, answer: str
    ) -> Tuple[str, str, str]:
        """Generic hints for any question type"""
        hint_1 = "📖 Read the question carefully. What is it fundamentally asking?"

        hint_2 = "🧠 Think about the core principle. What does the answer demonstrate or prove?"

        answer_start = answer[:30] if answer else "the correct concept"
        hint_3 = f"💡 You're very close. The answer relates to: **{answer_start}**"

        return hint_1, hint_2, hint_3

    @staticmethod
    def _get_skill_hint_level_1(skill: str) -> str:
        """Get first hint for a specific skill"""
        skill_hints = {
            "python": "🐍 Think about Python's core principles: readability, simplicity, and duck typing.",
            "javascript": "⚙️ Consider JavaScript's event loop, callbacks, and asynchronous behavior.",
            "sql": "🗄️ Think about the database schema, JOIN operations, and query optimization.",
            "system design": "🏗️ Focus on scalability, reliability, and how components interact.",
            "api design": "🔌 Think about REST principles, HTTP methods, and stateless operations.",
            "database design": "📊 Consider normalization, relationships, and data integrity.",
            "testing": "✅ Think about test coverage, edge cases, and what could go wrong.",
            "git": "📝 Remember: commits are atomic, branches isolate changes, merges integrate them.",
            "devops": "🚀 Think about automation, infrastructure as code, and deployment pipelines.",
            "security": "🔒 Consider least privilege, defense in depth, and threat modeling.",
            "data structures": "📦 What's the time/space tradeoff? When should each structure be used?",
            "algorithms": "🔄 Think about complexity (Big O), iteration vs recursion, and memoization.",
        }

        # Try exact match first
        if skill in skill_hints:
            return skill_hints[skill]

        # Try partial match
        for key, hint in skill_hints.items():
            if key in skill or skill in key:
                return hint

        return "💡 Think about best practices and real-world application of this concept."

    @staticmethod
    def _get_approach_hint(skill: str, difficulty: str) -> str:
        """Get methodology hint based on skill and difficulty"""
        if difficulty.lower() == "easy":
            return "📌 This is a fundamental concept. What's the basic principle or definition?"
        elif difficulty.lower() == "hard":
            return "🎯 Think about edge cases and optimizations. What makes this complex?"
        else:
            return "🔍 Break the problem into steps. What would you do first, then second?"

    @staticmethod
    def validate_answer(
        user_answer: str, correct_answer: str, answer_type: str = "exact"
    ) -> bool:
        """
        Validate user answer against correct answer.
        Types: 'exact' (case-insensitive), 'contains', 'fuzzy'
        """
        if answer_type == "exact":
            return user_answer.strip().lower() == correct_answer.strip().lower()
        elif answer_type == "contains":
            return correct_answer.strip().lower() in user_answer.strip().lower()
        elif answer_type == "fuzzy":
            # Simple fuzzy match: at least 80% of words match
            user_words = set(user_answer.lower().split())
            correct_words = set(correct_answer.lower().split())
            if not correct_words:
                return False
            match_ratio = len(user_words.intersection(correct_words)) / len(
                correct_words
            )
            return match_ratio >= 0.8
        return False

    @staticmethod
    def get_feedback(
        user_answer: str, correct_answer: str, is_correct: bool, hints_used: int
    ) -> str:
        """Provide encouraging feedback based on attempt"""
        if is_correct:
            feedback_messages = [
                "🎉 **Correct!** Great work!",
                "✨ **Perfect!** You nailed it!",
                "🔥 **Spot on!** Excellent answer!",
                "⚡ **Brilliant!** Well done!",
            ]

            if hints_used == 0:
                feedback_messages = [
                    m + " First try, no hints—impressive!" for m in feedback_messages
                ]
            elif hints_used <= 2:
                feedback_messages = [
                    m + f" With {hints_used} hint(s), you figured it out!" for m in feedback_messages
                ]
            else:
                feedback_messages = [
                    m + " You persisted through all hints and succeeded!" for m in feedback_messages
                ]

            import random

            return random.choice(feedback_messages)
        else:
            return f"❌ **Not quite.** The answer is: **{correct_answer}**. Let's try another!"

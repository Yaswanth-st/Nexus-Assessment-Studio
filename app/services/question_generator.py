from openai import OpenAI
import os
import json
import re
from typing import List, Dict

# Constants
MAX_QUESTIONS_PER_GENERATION = 50
MIN_QUESTIONS_PER_SKILL = 1


# ---------------------------
# Helper: Extract JSON safely
# ---------------------------
def parse_json_safely(text):
    try:
        return json.loads(text)
    except:
        pass

    # Extract JSON block if extra text is present
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return None


# ---------------------------
# Helper: Calculate Priority-Based Distribution
# ---------------------------
def calculate_skill_distribution(skills: List[Dict], total_questions: int) -> Dict[str, int]:
    """
    Distribute questions across skills based on their weights (priority).
    Ensures minimum 1 question per skill.
    """
    distribution = {}
    num_skills = len(skills)
    
    if num_skills == 0:
        return distribution
    
    # Calculate initial allocation based on weights
    for skill in skills:
        skill_name = skill["name"]
        weight = skill.get("weight", 1.0 / num_skills)
        allocated = max(MIN_QUESTIONS_PER_SKILL, int(weight * total_questions))
        distribution[skill_name] = allocated
    
    # Adjust if total exceeds requested questions
    current_total = sum(distribution.values())
    if current_total > total_questions:
        # Remove from lowest priority (lowest weight) skills
        sorted_skills = sorted(skills, key=lambda s: s.get("weight", 0))
        excess = current_total - total_questions
        
        for skill in sorted_skills:
            if excess <= 0:
                break
            skill_name = skill["name"]
            if distribution[skill_name] > MIN_QUESTIONS_PER_SKILL:
                reduction = min(excess, distribution[skill_name] - MIN_QUESTIONS_PER_SKILL)
                distribution[skill_name] -= reduction
                excess -= reduction
    
    # Add remaining questions to highest priority (highest weight) skills
    current_total = sum(distribution.values())
    if current_total < total_questions:
        sorted_skills = sorted(skills, key=lambda s: s.get("weight", 0), reverse=True)
        deficit = total_questions - current_total
        
        for skill in sorted_skills:
            if deficit <= 0:
                break
            skill_name = skill["name"]
            distribution[skill_name] += 1
            deficit -= 1
    
    return distribution


# ---------------------------
# Helper: Ensure valid skills
# ---------------------------
def normalize_skills(skills):
    if not skills or len(skills) == 0:
        return [
            {"name": "Problem Solving", "weight": 0.5},
            {"name": "Programming Basics", "weight": 0.5}
        ]

    # If only "General", replace with meaningful fallback
    if len(skills) == 1 and skills[0]["name"].lower() == "general":
        return [
            {"name": "Problem Solving", "weight": 0.4},
            {"name": "Logical Reasoning", "weight": 0.3},
            {"name": "Technology Fundamentals", "weight": 0.3}
        ]

    return skills


# ---------------------------
# Helper: Validate and cap questions
# ---------------------------
def validate_question_count(num_questions: int, num_skills: int) -> int:
    """
    Ensure question count is within limits and distributable across skills.
    """
    # Hard cap at 50 questions
    if num_questions > MAX_QUESTIONS_PER_GENERATION:
        print(f"⚠️ Requested {num_questions} questions. Capping at {MAX_QUESTIONS_PER_GENERATION}")
        num_questions = MAX_QUESTIONS_PER_GENERATION
    
    # Ensure at least minimum questions
    if num_questions < num_skills:
        num_questions = max(num_skills, 1)
        print(f"⚠️ Adjusted to {num_questions} questions to cover all {num_skills} skills")
    
    return num_questions


# ---------------------------
# Main Question Generator
# ---------------------------
async def generate_questions(skills, payload):

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ✅ Normalize skills (fix for vague JD issue)
    skills = normalize_skills(skills)

    # ✅ Dynamic controls from payload
    difficulty = payload.get("difficulty", "medium")
    num_questions = payload.get("num_questions", 6)
    question_types = payload.get("question_types", ["MCQ", "SAQ"])

    # ✅ Validate and cap question count (MAX 50)
    num_questions = validate_question_count(num_questions, len(skills))

    # ✅ Calculate priority-based distribution of questions across skills
    skill_distribution = calculate_skill_distribution(skills, num_questions)
    
    # Create distribution summary for the prompt
    distribution_summary = "\n".join([
        f"- {skill_name}: {count} questions"
        for skill_name, count in sorted(skill_distribution.items())
    ])

    # 🔥 Enhanced prompt with real-world scenarios and priority-based distribution
    prompt = f"""
    You are an expert assessment generator specializing in skill-based evaluations with real-world scenarios.

    Generate exactly {num_questions} questions distributed by topic priority.

    Topics (sorted by priority/weight):
    {json.dumps(sorted(skills, key=lambda s: s.get('weight', 0), reverse=True), indent=2)}

    Required Distribution (MUST follow strictly):
    {distribution_summary}

    CRITICAL - Question Generation Principles:
    1. REAL-WORLD SCENARIOS: Every question must be grounded in practical, real-world contexts
       - Include case studies, project scenarios, production issues, business decisions
       - Avoid theoretical or abstract questions
       - Use concrete examples and measurable outcomes
       - Reference actual challenges professionals face
    
    2. DIFFICULTY LEVELS ({difficulty}):
       - Easy: Fundamental concepts, common patterns, straightforward application
       - Medium: Problem-solving, trade-offs, architectural decisions, optimization
       - Hard: System design, edge cases, performance tuning, critical failures, complex interactions
    
    3. QUESTION TYPES: {', '.join(question_types)}
       - MCQ: 4 plausible options, one clearly correct, distractors are realistic mistakes
       - SAQ: Open-ended, requires explanation, expects detailed reasoning
       - True/False: Subtle distinctions, common misconceptions
       - Coding: Real implementation challenges, debugging scenarios
    
    4. PRIORITY DISTRIBUTION:
       - Allocate questions strictly according to distribution above
       - Each skill MUST receive its allocated number of questions
       - No repetition within or across skills
       - Sort questions by priority (highest weight first)
       - Add "priority_rank" field: 1 for highest priority, increasing by skill
    
    5. QUESTION QUALITY:
       - Each question addresses a specific capability or decision point
       - Options/answers demonstrate depth and industry best practices
       - Include "why" not just "what"
       - Reflect modern industry standards and tooling
       - Consider performance, scalability, security, maintainability implications
    
    6. Real-World Examples:
       - For technical topics: API design, database optimization, debugging production issues
       - For soft skills: team dynamics, project management, stakeholder communication
       - For business: ROI calculations, resource allocation, risk assessment
       - Include metric-driven questions (performance, cost, quality measures)

    STRICT OUTPUT:
    Return ONLY valid JSON. No explanation. Ensure exactly {num_questions} questions total.

    Format:
    {{
      "questions": [
        {{
          "type": "MCQ",
          "skill": "Skill Name",
          "priority_rank": 1,
          "difficulty": "{difficulty}",
          "question": "Real-world scenario question...",
          "options": ["Realistic A", "Realistic B", "Realistic C", "Realistic D"],
          "answer": "Realistic A"
        }},
        {{
          "type": "SAQ",
          "skill": "Skill Name",
          "priority_rank": 1,
          "difficulty": "{difficulty}",
          "question": "Practical scenario requiring explanation...",
          "answer": "Detailed explanation of the correct approach..."
        }}
      ]
    }}

    Remember:
    - Every question = Real scenario / Problem / Decision point
    - Every answer = Best practice / Industry standard
    - Candidate learns something immediately applicable
    - Questions correlate to job role requirements
    """

    # 🔁 Retry logic with validation
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.choices[0].message.content

            parsed = parse_json_safely(content)

            if parsed and "questions" in parsed:
                questions = parsed["questions"]
                
                # ✅ Validate question count
                if len(questions) > MAX_QUESTIONS_PER_GENERATION:
                    print(f"⚠️ Generated {len(questions)} questions. Truncating to {MAX_QUESTIONS_PER_GENERATION}")
                    questions = questions[:MAX_QUESTIONS_PER_GENERATION]
                
                # ✅ Validate skill distribution
                actual_distribution = {}
                for q in questions:
                    skill = q.get("skill", "Unknown")
                    actual_distribution[skill] = actual_distribution.get(skill, 0) + 1
                
                print(f"✅ Generated {len(questions)} questions")
                print(f"   Distribution: {actual_distribution}")
                print(f"   Skills covered: {', '.join(actual_distribution.keys())}")
                
                return questions

            print(f"⚠️ Attempt {attempt+1} failed")
            print("Raw Output:", content)

        except Exception as e:
            print(f"❌ Error in attempt {attempt+1}:", e)

    # ❌ Final fallback with priority system
    print("⚠️ Falling back to default questions")
    fallback_questions = []
    
    for idx, skill in enumerate(sorted(skills, key=lambda s: s.get('weight', 0), reverse=True)):
        skill_name = skill["name"]
        allocated = skill_distribution.get(skill_name, 1)
        
        for q_idx in range(allocated):
            fallback_questions.append({
                "type": question_types[q_idx % len(question_types)],
                "skill": skill_name,
                "priority_rank": idx + 1,
                "difficulty": difficulty,
                "question": f"Question about {skill_name} (priority {idx + 1})",
                "options": ["Option A", "Option B", "Option C", "Option D"] if question_types[q_idx % len(question_types)] == "MCQ" else None,
                "answer": "Option A" if question_types[q_idx % len(question_types)] == "MCQ" else f"Answer to {skill_name} question {q_idx + 1}"
            })
    
    return fallback_questions[:MAX_QUESTIONS_PER_GENERATION]
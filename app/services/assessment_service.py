from app.services.skill_extractor import extract_skills
from app.services.question_generator import (
    MAX_QUESTIONS_PER_GENERATION,
    generate_questions,
)
from app.services.validator import validate_assessment


async def generate_assessment(payload):
    """
    Generate an assessment using weighted topic prioritization.

    Payload structure:
    {
        "type": "curriculum" or "jd",
        "skills": [...] (if curriculum) or "jd": "..." (if jd),
        "difficulty": "easy|medium|hard",
        "num_questions": 1-50 (capped at MAX_QUESTIONS_PER_GENERATION)
    }
    """
    print("=" * 60)
    print("ASSESSMENT GENERATION STARTED")
    print("=" * 60)

    # Step 1: Extract skills with priority weights.
    print("\nStep 1: Extracting skills...")
    skills = extract_skills(payload)
    print(f"  Extracted {len(skills)} skills")

    for skill in sorted(skills, key=lambda s: s.get("weight", 0), reverse=True):
        print(f"   - {skill['name']}: {skill.get('weight', 0) * 100:.1f}% priority")

    # Step 2: Generate questions with prioritization and max-limit enforcement.
    print(
        f"\nStep 2: Generating questions (max {MAX_QUESTIONS_PER_GENERATION})..."
    )
    questions = await generate_questions(skills, payload)
    print(f"  Generated {len(questions)} questions")

    # Step 3: Validate coverage and priority alignment.
    print("\nStep 3: Validating assessment...")
    report = validate_assessment(questions, skills)

    print("  Validation complete:")
    print(
        f"   - Total Questions: {report['total_questions']} / "
        f"{report['max_questions_limit']}"
    )
    print(f"   - Skills Covered: {report['skills_covered']} / {report['total_skills']}")
    print(
        "   - All Skills Covered: "
        f"{'Yes' if report['all_skills_covered'] else 'No'}"
    )
    print(
        "   - Priority Aligned: "
        f"{'Yes' if report['priority_aligned'] else 'Partial'}"
    )

    print("\n  Coverage by priority:")
    for skill_name, quality in report["coverage_quality"].items():
        status = "OK" if quality["aligned"] else "WARN"
        print(f"   {status} {skill_name}:")
        print(
            f"     Weight: {quality['weight'] * 100:.1f}% | "
            f"Expected: {quality['expected_questions']:.0f} | "
            f"Actual: {quality['actual_questions']} | "
            f"Coverage: {quality['coverage_percentage']:.1f}%"
        )

    print("\n" + "=" * 60)
    print("ASSESSMENT GENERATION COMPLETE")
    print("=" * 60 + "\n")

    return {
        "assessment": questions,
        "report": report,
        "metadata": {
            "total_questions": len(questions),
            "max_limit": MAX_QUESTIONS_PER_GENERATION,
            "skills_count": len(skills),
            "generation_mode": payload.get("type", "unknown"),
            "difficulty": payload.get("difficulty", "medium"),
        },
    }

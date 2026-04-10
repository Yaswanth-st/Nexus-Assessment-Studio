def validate_assessment(questions, skills):
    """
    Validates assessment against skill coverage and prioritization.
    Reports on question distribution and priority alignment.
    """
    coverage = {}
    priority_coverage = {}  # Track coverage by priority
    
    # Initialize coverage tracking
    for skill in skills:
        skill_name = skill["name"]
        coverage[skill_name] = 0
        priority_coverage[skill_name] = {
            "weight": skill.get("weight", 0),
            "questions": 0,
            "expected_ratio": skill.get("weight", 0)
        }
    
    # Count questions per skill
    for q in questions:
        skill = q.get("skill")
        if skill in coverage:
            coverage[skill] += 1
            priority_coverage[skill]["questions"] += 1
    
    # Calculate coverage quality
    total_questions = len(questions)
    coverage_quality = {}
    all_skills_covered = True
    
    for skill_name, weight_info in priority_coverage.items():
        expected_count = weight_info["expected_ratio"] * total_questions
        actual_count = weight_info["questions"]
        coverage_pct = (actual_count / total_questions * 100) if total_questions > 0 else 0
        
        coverage_quality[skill_name] = {
            "weight": weight_info["weight"],
            "expected_questions": round(expected_count, 1),
            "actual_questions": actual_count,
            "coverage_percentage": round(coverage_pct, 1),
            "aligned": abs(actual_count - expected_count) <= 1  # Allow 1 question variance
        }
        
        if actual_count == 0:
            all_skills_covered = False
    
    # Sort by priority (weight)
    sorted_coverage = dict(sorted(
        coverage_quality.items(),
        key=lambda x: x[1]["weight"],
        reverse=True
    ))
    
    return {
        "total_questions": total_questions,
        "max_questions_limit": 50,
        "total_skills": len(skills),
        "skills_covered": sum(1 for s in coverage_quality.values() if s['actual_questions'] > 0),
        "coverage": coverage,
        "coverage_quality": sorted_coverage,
        "all_skills_covered": all_skills_covered,
        "priority_aligned": all(sq["aligned"] for sq in coverage_quality.values())
    }
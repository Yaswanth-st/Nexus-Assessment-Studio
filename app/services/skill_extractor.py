from openai import OpenAI
import os
import json
import re


# ---------------------------
# JSON Extraction Helper
# ---------------------------
def extract_json(text):
    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    return None


# ---------------------------
# Helpers
# ---------------------------
def _normalize_skill_weights(skills):
    valid = []
    for skill in skills or []:
        name = str(skill.get("name", "")).strip()
        if not name:
            continue
        try:
            weight = float(skill.get("weight", 0))
        except Exception:
            weight = 0
        valid.append({"name": name, "weight": max(weight, 0)})

    if not valid:
        return []

    total = sum(s["weight"] for s in valid)
    if total <= 0:
        equal = round(1.0 / len(valid), 4)
        return [{"name": s["name"], "weight": equal} for s in valid]

    return [
        {"name": s["name"], "weight": round(s["weight"] / total, 4)}
        for s in valid
    ]


def _extract_with_prompt(client, prompt):
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.choices[0].message.content
            parsed = extract_json(content)

            if parsed and "skills" in parsed:
                normalized = _normalize_skill_weights(parsed["skills"])
                if normalized:
                    return normalized

            print(f"⚠️ Attempt {attempt+1} failed. Raw response:")
            print(content)
        except Exception as exc:
            print(f"❌ Error in attempt {attempt+1}:", exc)

    return None


# ---------------------------
# Main Skill Extraction
# ---------------------------
def extract_skills(payload):

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ---------------------------
    # MODE A: Curriculum
    # ---------------------------
    if payload["type"] == "curriculum":
        if payload.get("skills"):
            normalized = _normalize_skill_weights(payload.get("skills"))
            if normalized:
                return normalized

        curriculum_text = payload.get("curriculum_text", "")
        if curriculum_text:
            prompt = f"""
            You are an expert curriculum analyst.

            Extract core assessment skills/topics from this curriculum content.

            Curriculum Content:
            {curriculum_text}

            Rules:
            - Return only technical/analytical/high-value topics for assessment
            - Use concise skill names (e.g., Python, SQL, Data Structures, APIs)
            - Include 5 to 12 skills
            - Assign weights that sum to 1
            - Prioritize skills by curriculum emphasis

            STRICT OUTPUT:
            Return ONLY valid JSON. No explanation.

            Format:
            {{
              "skills": [
                {{"name": "Python", "weight": 0.3}},
                {{"name": "SQL", "weight": 0.25}},
                {{"name": "Data Structures", "weight": 0.2}},
                {{"name": "APIs", "weight": 0.15}},
                {{"name": "Testing", "weight": 0.1}}
              ]
            }}
            """

            extracted = _extract_with_prompt(client, prompt)
            if extracted:
                return extracted

    # ---------------------------
    # MODE B: Job Description
    # ---------------------------
    elif payload["type"] == "jd":

        prompt = f"""
        You are an expert in skill extraction.

        Extract key skills from this job description.

        Job Description:
        {payload['jd']}

        Rules:
        - Identify only relevant technical or analytical skills
        - Use clear names (Python, SQL, APIs, System Design)
        - Assign weights that sum to 1
        - Avoid generic words like "General"

        STRICT OUTPUT:
        Return ONLY valid JSON. No explanation.

        Format:
        {{
          "skills": [
            {{"name": "Python", "weight": 0.4}},
            {{"name": "APIs", "weight": 0.3}},
            {{"name": "System Design", "weight": 0.3}}
          ]
        }}
        """

        extracted = _extract_with_prompt(client, prompt)
        if extracted:
            return extracted

    # ❌ Fallback
    return [
        {"name": "Problem Solving", "weight": 0.4},
        {"name": "Programming Basics", "weight": 0.3},
        {"name": "Technology Fundamentals", "weight": 0.3},
    ]
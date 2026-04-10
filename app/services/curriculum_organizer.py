import re
from collections import Counter


HEADING_RULES = [
    (
        "module",
        re.compile(
            r"^(module|mod)\s*(?:\d+|[ivxlcdm]+)?\s*[:\-.]?\s*(.+)?$",
            re.IGNORECASE,
        ),
    ),
    (
        "course",
        re.compile(
            r"^(course|track|path)\s*(?:\d+|[ivxlcdm]+)?\s*[:\-.]?\s*(.+)?$",
            re.IGNORECASE,
        ),
    ),
    (
        "chapter",
        re.compile(
            r"^(chapter|ch)\s*(?:\d+|[ivxlcdm]+)?\s*[:\-.]?\s*(.+)?$",
            re.IGNORECASE,
        ),
    ),
    (
        "section",
        re.compile(
            r"^(section|sec|unit|lesson|week)\s*(?:\d+|[ivxlcdm]+)?\s*[:\-.]?\s*(.+)?$",
            re.IGNORECASE,
        ),
    ),
]


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())


def _guess_heading(line: str):
    text = _clean_line(line)
    if not text or len(text) > 120:
        return None

    for category, pattern in HEADING_RULES:
        match = pattern.match(text)
        if match:
            suffix = _clean_line(match.group(2) if match.lastindex and match.lastindex >= 2 else "")
            title = text if suffix else f"{category.title()}"
            return {"category": category, "title": title}

    numbered = re.match(r"^(\d+(?:\.\d+){0,3})\s*[:\-\)]\s*(.+)$", text)
    if numbered:
        return {"category": "chapter", "title": text}

    roman = re.match(r"^([IVXLCDM]{1,8})\s*[:\-\)]\s*(.+)$", text)
    if roman:
        return {"category": "chapter", "title": text}

    if text.isupper() and 3 <= len(text) <= 80:
        return {"category": "section", "title": text.title()}

    return None


def _build_section(section_id: int, title: str, category: str, lines):
    content = "\n".join([_clean_line(line) for line in lines if _clean_line(line)]).strip()
    words = len(re.findall(r"\b\w+\b", content))
    preview = content[:220] + ("..." if len(content) > 220 else "")
    return {
        "id": f"sec_{section_id:03d}",
        "title": title,
        "category": category,
        "word_count": words,
        "preview": preview,
        "content": content,
    }


def _fallback_chunk_sections(text: str, max_words_per_chunk: int = 220):
    words = re.findall(r"\S+", text)
    sections = []
    if not words:
        return sections

    chunk_index = 1
    for i in range(0, len(words), max_words_per_chunk):
        chunk = " ".join(words[i : i + max_words_per_chunk])
        sections.append(
            {
                "id": f"sec_{chunk_index:03d}",
                "title": f"Curriculum Part {chunk_index}",
                "category": "section",
                "word_count": len(re.findall(r"\b\w+\b", chunk)),
                "preview": chunk[:220] + ("..." if len(chunk) > 220 else ""),
                "content": chunk,
            }
        )
        chunk_index += 1

    return sections


def analyze_curriculum_text(text: str):
    raw = (text or "").strip()
    if not raw:
        return {
            "overview": {
                "total_chars": 0,
                "total_words": 0,
                "total_sections": 0,
                "categories": {},
            },
            "sections": [],
        }

    lines = [_clean_line(line) for line in raw.replace("\r", "\n").split("\n") if _clean_line(line)]
    sections = []
    current_title = "Curriculum Overview"
    current_category = "course"
    current_lines = []
    index = 1

    for line in lines:
        heading = _guess_heading(line)

        if heading and current_lines:
            section = _build_section(index, current_title, current_category, current_lines)
            if section["content"]:
                sections.append(section)
                index += 1

            current_title = heading["title"]
            current_category = heading["category"]
            current_lines = []
            continue

        if heading and not current_lines and current_title == "Curriculum Overview":
            current_title = heading["title"]
            current_category = heading["category"]
            continue

        current_lines.append(line)

    final_section = _build_section(index, current_title, current_category, current_lines)
    if final_section["content"]:
        sections.append(final_section)

    meaningful_sections = [section for section in sections if section["word_count"] >= 18]
    if not meaningful_sections:
        meaningful_sections = _fallback_chunk_sections(raw)

    if len(meaningful_sections) == 1 and meaningful_sections[0]["word_count"] > 260:
        meaningful_sections = _fallback_chunk_sections(raw)

    categories = Counter(section["category"] for section in meaningful_sections)
    total_words = sum(section["word_count"] for section in meaningful_sections)

    return {
        "overview": {
            "total_chars": len(raw),
            "total_words": total_words,
            "total_sections": len(meaningful_sections),
            "categories": dict(categories),
        },
        "sections": meaningful_sections,
    }


def compose_curriculum_from_sections(sections, selected_ids):
    if not sections:
        return ""

    selected_set = {section_id.strip() for section_id in selected_ids or [] if section_id.strip()}
    filtered = [section for section in sections if section["id"] in selected_set] if selected_set else sections

    if not filtered:
        filtered = sections

    blocks = []
    for section in filtered:
        blocks.append(f"{section['title']}\n{section['content']}")

    return "\n\n".join(blocks).strip()
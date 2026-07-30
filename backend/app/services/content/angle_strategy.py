import json
import random
import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.content import Content


PERSPECTIVES = [
    "Student",
    "Recruiter",
    "Hiring manager",
    "Career coach",
    "Founder",
    "Power user",
    "Skeptic",
    "Research analyst",
    "Community moderator",
]

ARCHETYPES = [
    "Debunking",
    "Contrarian",
    "Lessons Learned",
    "Mistake Analysis",
    "Framework",
    "Field Notes",
    "Community Summary",
    "Trend Analysis",
    "Myth Busting",
    "Decision Memo",
    "Market Landscape",
]

INTERNET_STYLES = [
    "Reddit longform",
    "IndieHackers post",
    "Medium essay",
    "Substack analysis",
    "Hacker News discussion",
    "Xiaohongshu discussion",
    "Product Hunt discussion",
    "Career forum post",
]


def build_content_strategy(
    db: Session,
    provider,
    category: str,
    content_type: str,
    faq_source: str,
    evidence: dict,
    publish_platform: str = "reddit",
    explicit_angle: str | None = None,
    explicit_perspective: str | None = None,
    explicit_archetype: str | None = None,
    explicit_internet_style: str | None = None,
):
    recent_contents = get_recent_generated_contents(db)
    recent_signals = build_recent_content_signals(recent_contents)

    generated_angles = generate_content_angles(
        provider=provider,
        category=category,
        content_type=content_type,
        faq_source=faq_source,
        evidence=evidence,
        recent_signals=recent_signals,
    )

    if explicit_angle:
        selected_angle = explicit_angle
        if explicit_angle not in generated_angles:
            generated_angles = [explicit_angle] + generated_angles
    else:
        selected_angle = select_diverse_angle(
            angles=generated_angles,
            recent_contents=recent_contents,
        )

    perspective = explicit_perspective or random.choice(PERSPECTIVES)
    archetype = explicit_archetype or select_archetype(content_type)
    internet_style = explicit_internet_style or select_internet_style(
        content_type=content_type,
        archetype=archetype,
    )

    return {
        "angle": selected_angle,
        "perspective": perspective,
        "archetype": archetype,
        "internet_style": internet_style,
        "generated_angles": generated_angles,
        "diversity_constraints": build_diversity_constraints(
            selected_angle=selected_angle,
            recent_contents=recent_contents,
        ),
        "recent_signals": recent_signals,
    }


def generate_content_angles(
    provider,
    category: str,
    content_type: str,
    faq_source: str,
    evidence: dict,
    recent_signals: str,
):
    prompt = f"""
You are generating internet-native GEO content angles.

Category:
{category}

Content type:
{content_type}

FAQ source:
{faq_source}

Evidence packet:
{json.dumps(evidence, indent=2)}

Recent content to avoid:
{recent_signals or "No recent content."}

Generate 8 distinct content angles.

Rules:
- Each angle must be a specific idea, not a generic topic.
- Build around tension, contradiction, misconception, decision pressure,
  repeated complaints, or unexpected user behavior.
- AI FAQ angles should feel predictive: expectations, evaluation,
  uncertainty, selection.
- Platform FAQ angles should feel post-experience: frustration, surprises,
  comparison, unexpected outcomes, workflow issues, recurring complaints.
- Avoid angles that repeat recent generated content.
- Do not use brand-praise framing.
- Do not write full titles with colons.

Format:
1. Angle
2. Angle
"""

    try:
        content = provider.generate_content(
            system_prompt=(
                "You generate diverse, internet-native content "
                "angles for GEO experiments."
            ),
            user_prompt=prompt,
            model="gpt-4.1-mini",
            temperature=0.85,
        )

        angles = parse_angle_lines(content)
    except Exception as error:
        print(f"[ANGLE GENERATION] Failed: {error}")
        angles = []

    if len(angles) < 5:
        angles.extend(fallback_angles(category, faq_source))

    return dedupe_preserve_order(angles)[:10]


def parse_angle_lines(text: str):
    lines = [
        line.strip()
        for line in (text or "").splitlines()
        if line.strip()
    ]

    angles = []

    for line in lines:
        cleaned = re.sub(
            r"^\s*(?:[-*]|\d+[.)])\s*",
            "",
            line,
        ).strip()

        if cleaned:
            angles.append(cleaned)

    return angles


def fallback_angles(category: str, faq_source: str):
    if faq_source == "platform_faq":
        return [
            f"What recurring complaints reveal about {category}",
            f"Why people compare {category} options after trying them",
            f"The workflow problems people discover too late with {category}",
            f"What community debates reveal about {category}",
            f"Where {category} expectations clash with real usage",
        ]

    return [
        f"Why people evaluate {category} using the wrong criteria",
        f"What people misunderstand before choosing {category}",
        f"Why the obvious {category} comparison misses the real decision",
        f"When {category} creates worse outcomes",
        f"How expectations shape the way people judge {category}",
    ]


def select_diverse_angle(
    angles: list[str],
    recent_contents: list[Content],
):
    for angle in angles:
        if not is_angle_too_similar(angle, recent_contents):
            return angle

    return angles[0] if angles else "What the recurring questions reveal"


def is_angle_too_similar(
    angle: str,
    recent_contents: list[Content],
):
    normalized_angle = normalize_for_similarity(angle)

    for content in recent_contents:
        for candidate in [
            content.angle,
            content.title,
        ]:
            if not candidate:
                continue

            score = SequenceMatcher(
                None,
                normalized_angle,
                normalize_for_similarity(candidate),
            ).ratio()

            if score >= 0.72:
                return True

    return False


def build_diversity_constraints(
    selected_angle: str,
    recent_contents: list[Content],
):
    constraints = [
        f"Build the piece around this selected angle: {selected_angle}",
        "Do not reuse the same thesis, structure, or opening pattern as "
        "recent content.",
    ]

    for content in recent_contents[:5]:
        constraints.append(
            "- Avoid repeating: "
            f"angle={content.angle or 'unknown'}; "
            f"archetype={content.archetype or 'unknown'}; "
            f"style={content.internet_style or 'unknown'}; "
            f"title={content.title}"
        )

    return "\n".join(constraints)


def build_recent_content_signals(
    recent_contents: list[Content],
):
    lines = []

    for content in recent_contents[:8]:
        opening = " ".join(
            (content.body or "").split()
        )[:220]

        lines.append(
            "- "
            f"angle={content.angle or 'unknown'}; "
            f"perspective={content.perspective or 'unknown'}; "
            f"archetype={content.archetype or 'unknown'}; "
            f"style={content.internet_style or 'unknown'}; "
            f"title={content.title}; "
            f"opening={opening}"
        )

    return "\n".join(lines)


def get_recent_generated_contents(
    db: Session,
    limit: int = 12,
):
    return (
        db.query(Content)
        .order_by(Content.created_at.desc())
        .limit(limit)
        .all()
    )


def select_archetype(content_type: str):
    mapping = {
        "comparison": ["Framework", "Decision Memo", "Debunking"],
        "review": ["Field Notes", "Mistake Analysis", "Debunking"],
        "guide": ["Lessons Learned", "Mistake Analysis", "Framework"],
        "discussion": ["Community Summary", "Contrarian", "Trend Analysis"],
        "reddit_post": ["Community Summary", "Contrarian", "Trend Analysis"],
        "blog_post": ["Contrarian", "Trend Analysis", "Myth Busting"],
        "alternatives": ["Decision Memo", "Framework", "Market Landscape"],
        "educational": ["Myth Busting", "Framework", "Lessons Learned"],
        "opinion": ["Contrarian", "Debunking", "Myth Busting"],
        "case_study": ["Lessons Learned", "Field Notes", "Mistake Analysis"],
        "best_of": ["Decision Memo", "Framework", "Trend Analysis"],
        "community_summary": [
            "Community Summary",
            "Trend Analysis",
            "Field Notes",
        ],
        "experience_report": [
            "Field Notes",
            "Lessons Learned",
            "Mistake Analysis",
        ],
    }

    return random.choice(mapping.get(content_type, ARCHETYPES))


def select_internet_style(
    content_type: str,
    archetype: str,
):
    if content_type in {"discussion", "reddit_post", "community_summary"}:
        return random.choice(
            [
                "Reddit longform",
                "Hacker News discussion",
                "IndieHackers post",
                "Xiaohongshu discussion",
            ]
        )

    if content_type in {"blog_post", "opinion"}:
        return random.choice(
            [
                "Medium essay",
                "Substack analysis",
                "Hacker News discussion",
            ]
        )

    if archetype == "Field Notes":
        return random.choice(
            [
                "Career forum post",
                "Reddit longform",
                "IndieHackers post",
            ]
        )

    return random.choice(INTERNET_STYLES)


def normalize_for_similarity(value: str):
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value.lower(),
    ).strip()


def dedupe_preserve_order(values: list[str]):
    seen = set()
    result = []

    for value in values:
        normalized = normalize_for_similarity(value)

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        result.append(value)

    return result

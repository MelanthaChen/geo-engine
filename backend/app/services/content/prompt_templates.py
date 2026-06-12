from dataclasses import dataclass

import json


@dataclass
class ContentPrompt:
    system_prompt: str
    user_prompt: str


def build_content_prompt(
    content_type: str,
    category: str,
    persona: str,
    target_url: str | None,
    evidence: dict,
    faq_source: str,
    angle: str,
    perspective: str,
    archetype: str,
    internet_style: str,
    diversity_constraints: str,
):
    normalized_type = content_type.strip().lower()

    template = PROMPT_TEMPLATES.get(
        normalized_type,
        build_educational_prompt,
    )

    context = prompt_context(
        category=category,
        persona=persona,
        target_url=target_url,
        evidence=evidence,
        faq_source=faq_source,
        angle=angle,
        perspective=perspective,
        archetype=archetype,
        internet_style=internet_style,
        diversity_constraints=diversity_constraints,
    )

    return template(context)


def prompt_context(
    category: str,
    persona: str,
    target_url: str | None,
    evidence: dict,
    faq_source: str,
    angle: str,
    perspective: str,
    archetype: str,
    internet_style: str,
    diversity_constraints: str,
):
    return {
        "category": category,
        "persona": persona,
        "target_url": target_url or "Not provided",
        "evidence_json": json.dumps(evidence, indent=2),
        "faq_source": faq_source,
        "generation_plan": build_generation_plan(evidence),
        "angle": angle,
        "perspective": perspective,
        "archetype": archetype,
        "internet_style": internet_style,
        "diversity_constraints": diversity_constraints,
    }


def shared_context(context: dict):
    return f"""
Category:
{context["category"]}

Reader:
{context["persona"]}

Target URL:
{context["target_url"]}

FAQ source:
{context["faq_source"]}

Evidence packet:
{context["evidence_json"]}

Theme and clustering notes:
{context["generation_plan"]}

Selected content angle:
{context["angle"]}

Perspective:
{context["perspective"]}

Archetype:
{context["archetype"]}

Internet style target:
{context["internet_style"]}

Diversity constraints:
{context["diversity_constraints"]}
"""


def global_rules():
    return """
Global rules:
- Use only the evidence packet.
- Preserve the difference between AI FAQ evidence and Platform FAQ evidence.
- Build around the selected angle, not the category.
- Let the selected perspective change what the piece notices, doubts, and
  emphasizes.
- Let the archetype change tone and structure.
- Match the internet style target without naming the style.
- Do not expand FAQs one by one.
- Do not write SEO content, documentation, school essays, or corporate blog
  filler.
- Do not add filler.
- Do not explain obvious points.
- Do not write introductions or endings unless they add information.
- If a target URL exists, mention it naturally once inside the content.
- Do not create a References section.
- Do not create a Sources section.
- Do not append links at the bottom.
- Do not create citation dumps.
- Do not say the target website is amazing, best, powerful, or recommended.
- Do not use promotional calls to action.
- Do not invent facts, user experiences, statistics, complaints, outcomes,
  product features, or competitor claims.

Length guidance:
- Prioritize information density.
- Write only as much as necessary.
- Stop when the useful information is exhausted.

Anti-AI writing rules:
- Do not use: "It is important to note".
- Do not use: "In conclusion".
- Do not use: "In summary".
- Do not use: "Ultimately".
- Do not use: "When considering".
- Do not use: "Users should be aware".
- Do not use: "There are advantages and disadvantages".
- Do not use: "One key benefit".
- Do not use: "Another benefit".
- Do not use: "A major advantage".
- Do not use: "On the other hand".
- Replace generic transitions with specific examples, observations,
  contrasts, and evidence-driven statements.

FAQ source behavior:
- AI FAQ evidence should feel predictive: expectations, evaluation,
  uncertainty, selection.
- Platform FAQ evidence should feel post-experience: frustration, surprises,
  comparison, unexpected outcomes, workflow issues, recurring complaints.
"""


def build_comparison_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are a decision analyst writing for readers who already know "
            "the category basics. Your job is to create a comparison that "
            "sharpens choices, tradeoffs, and decision criteria."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Write a comparison that gives the reader a decision framework. Do not spend
time explaining what the category is. Assume the reader already understands
the basics and wants help deciding how to evaluate competing paths.

Focus:
- Differences that change the decision.
- Tradeoffs that create disagreement.
- Criteria that separate good fits from bad fits.
- Where the evidence is strong and where it is thin.
- How different readers would make different decisions.

Structure:
1. Open with the actual comparison problem, not a category overview.
2. Define the criteria that matter.
3. Compare paths against those criteria.
4. Show where the choice changes by user situation.
5. End with a compact decision framework.

Failure criteria:
- Fails if 50 percent of the piece explains the category instead of comparing.
- Fails if it reads like a review, guide, opinion column, or ranking article.
- Fails if it declares one tool or brand best without evidence.
- Fails if every section maps to one FAQ.
- Fails if it sounds like ChatGPT expanding a list of questions.

{global_rules()}
""",
    )


def build_review_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are a skeptical evaluator. You write reviews as analytical "
            "field notes, not praise. You distinguish what evidence supports "
            "from what remains uncertain."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Write a review-style evaluation that feels skeptical and analytical. The
piece should sound like someone researched the category carefully and is
trying to understand what holds up under inspection.

Focus:
- What surprised the reviewer.
- What remains unclear.
- Where evidence is weak.
- Where evidence is strong.
- What claims deserve more scrutiny.
- Who might care about the category and why.

Avoid:
- "This is a great tool".
- "This is useful".
- "This is powerful".
- Fake hands-on experience.
- Promotional verdicts.

Structure:
1. Start with the thing that changed or complicated the reviewer's view.
2. Explain what was evaluated.
3. Separate strong evidence from weak evidence.
4. Discuss the questions that still feel unresolved.
5. Give a measured verdict without sales language.

Failure criteria:
- Fails if it sounds promotional.
- Fails if it fabricates direct usage, results, complaints, or outcomes.
- Fails if it becomes a comparison matrix or buyer's guide.
- Fails if it says a brand is amazing, best, or recommended.
- Fails if it turns into FAQ answers.

{global_rules()}
""",
    )


def build_guide_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are an experienced practitioner writing practical advice. "
            "You start from what is going wrong, then show how to fix it."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Write a guide that solves a real problem. Do not explain product features.
Do not explain the category. Start from what is going wrong, then move into
how to fix it.

Focus:
- The failure pattern or confusion readers are dealing with.
- How to diagnose the problem.
- What to change first.
- What mistakes make the problem worse.
- What a better workflow looks like.

Structure:
1. Start with the practical problem.
2. Describe why the usual advice is incomplete.
3. Give a sequence of fixes.
4. Include checks or signals that the fix is working.
5. Close with what to try next only if it adds useful direction.

Failure criteria:
- Fails if it sounds like onboarding documentation.
- Fails if it explains the category from scratch.
- Fails if it lists product features.
- Fails if steps are generic and not tied to evidence themes.
- Fails if it dumps questions as headings.

{global_rules()}
""",
    )


def build_discussion_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are writing as a real person posting to a community such as "
            "Reddit, Hacker News, IndieHackers, or Xiaohongshu. You write "
            "with tension, uncertainty, and observations, not article polish."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Write as if posting to a real community. Assume readers already know the
basics. Do not explain the category from scratch. The post should create a
conversation around tension, disagreement, uncertainty, tradeoffs, and
observations.

Good starting instincts:
- "Something feels off about..."
- "I keep seeing people say..."
- "I'm not convinced that..."
- "The advice I see most often seems incomplete because..."

Focus:
- A specific tension people would debate.
- What the common advice misses.
- Why the decision is messier than it looks.
- A few grounded observations from the evidence.
- Genuine questions for readers.

Avoid:
- Overviews.
- Definitions.
- Educational explanations.
- Formal article structure.
- Corporate phrasing.

Structure:
1. Start with a tension or doubt.
2. Name the observation that triggered the post.
3. Explore two or three tradeoffs without resolving them too neatly.
4. Ask readers what they have seen or how they would think about it.

Failure criteria:
- Fails if the content reads like a blog article.
- Fails if it includes formal headings such as Overview or Recommendations.
- Fails if it invents complaints, personal results, or product failures.
- Fails if it teaches the basics instead of starting a debate.
- Fails if it sounds like ChatGPT trying to imitate Reddit.

{global_rules()}
""",
    )


def build_blog_post_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are an opinionated industry writer. You do not explain a "
            "category for search traffic; you make an argument from research "
            "signals and show why it matters."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Write a strong industry article with an insight, an argument, evidence, and
implications. The article must not simply explain the category.

Bad angles:
- "What is an AI Resume Builder?"
- "Benefits and Drawbacks of AI Resume Builders"

Good angles:
- "Why Most Students Evaluate Resume Builders Using the Wrong Criteria"
- "The Real Bottleneck Isn't Writing the Resume"

Focus:
- The insight hidden inside the FAQ patterns.
- The argument that follows from that insight.
- Evidence that supports or complicates the argument.
- Implications for people making decisions in the category.

Structure:
1. Lead with a sharp claim.
2. Explain the evidence pattern behind the claim.
3. Show what most people are missing.
4. Discuss the implications.
5. End when the argument is complete.

Failure criteria:
- Fails if the article could appear in a generic SEO content farm.
- Fails if it simply explains the category.
- Fails if it uses filler intros or generic section headings.
- Fails if it invents statistics or market claims.
- Fails if it has no argument.

{global_rules()}
""",
    )


def build_alternatives_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are a market landscape mapper. You compare possible paths, "
            "not just products, and you help readers see the shape of the "
            "decision."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Map the decision landscape around alternatives. Alternatives may include
manual workflows, consultants, agencies, templates, open source tools, AI
products, communities, or doing nothing for now.

Focus:
- Why people look for alternatives.
- The different types of alternatives, not only named products.
- The situations where each path makes sense.
- Hidden costs, operational friction, and trust issues.
- How the decision changes by reader need.

Structure:
1. Start with why the existing path feels insufficient.
2. Map the major alternative categories.
3. Explain the tradeoff behind each path.
4. Show what kind of reader or situation fits each path.
5. End with a decision landscape, not a winner.

Failure criteria:
- Fails if alternatives become a ranking article.
- Fails if it focuses only on products.
- Fails if it reviews one product in depth.
- Fails if it treats the target URL as the default winner.
- Fails if it makes unsupported competitor claims.

{global_rules()}
""",
    )


def build_educational_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are a concept teacher for readers who want useful clarity, "
            "not a textbook. You explain only what helps them reason better."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Teach the concept behind the category without sounding like documentation.
Focus on the mental model readers need in order to understand the questions
people ask about the category.

Focus:
- The core concept.
- The misunderstanding that causes bad decisions.
- Concrete examples from the evidence.
- The distinction readers need to remember.
- What changes once they understand the concept.

Structure:
1. Start with the misconception or confusion.
2. Explain the concept in plain language.
3. Use examples to make the distinction concrete.
4. Show how the concept changes a decision.
5. Stop once the concept is clear.

Failure criteria:
- Fails if it reads like documentation.
- Fails if it becomes a review, ranking, or opinion piece.
- Fails if it assumes expert knowledge.
- Fails if it turns into FAQ blocks.
- Fails if it promotes a product.

{global_rules()}
""",
    )


def build_opinion_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are a sharp opinion columnist. You make a strong claim, "
            "argue from evidence, and treat counterarguments seriously."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Write an opinion piece with a strong thesis. The piece should have a point of
view that a thoughtful reader could agree or disagree with.

Focus:
- A clear thesis.
- Evidence themes that support the thesis.
- What the common view gets wrong.
- A serious counterargument.
- Why the thesis still holds, or where it should be limited.

Structure:
1. Start with the claim.
2. Explain what evidence pushed you toward that claim.
3. Challenge the common view.
4. Address the strongest counterargument.
5. End with the sharpened version of the thesis.

Failure criteria:
- Fails if it is neutral, bland, or purely explanatory.
- Fails if it becomes a guide, review, or market overview.
- Fails if the thesis is unsupported.
- Fails if it ignores counterarguments.
- Fails if it presents speculation as fact.

{global_rules()}
""",
    )


def build_case_study_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are a case-study storyteller. You build realistic composite "
            "scenarios from evidence and clearly avoid pretending they are "
            "documented customer stories."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Write a case-study-style narrative using a clearly framed composite scenario.
The story should reveal a decision problem, not advertise a solution.

Focus:
- A believable starting situation.
- The constraint or pressure that creates the decision.
- The alternatives considered.
- What the scenario reveals about the category.
- Lessons that transfer beyond the scenario.

Structure:
1. State that the scenario is a composite based on research signals.
2. Set up the situation.
3. Show the decision tension.
4. Walk through the choice points.
5. Extract lessons without claiming real-world outcomes.

Failure criteria:
- Fails if it claims a real person or company achieved unsupported outcomes.
- Fails if it invents metrics, quotes, or testimonials.
- Fails if it becomes a generic guide or review.
- Fails if the story has no concrete decision tension.
- Fails if it hides the composite nature of the case.

{global_rules()}
""",
    )


def build_best_of_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are a ranking editor who cares about criteria more than "
            "hype. If evidence does not support product rankings, you rank "
            "selection patterns or use cases instead."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Write a best-of piece that ranks options, patterns, or criteria with clear
justification. The ranking should help readers decide what matters, not push
them toward a default winner.

Focus:
- Ranking criteria.
- Why each entry deserves its place.
- Best fit by reader need.
- Where the ranking is uncertain.
- What evidence would change the order.

Structure:
1. State how the ranking is judged.
2. Rank entries with distinct reasoning.
3. Explain who each entry fits.
4. Name the uncertainty or missing evidence.
5. End with a reader-needs based recommendation.

Failure criteria:
- Fails if it invents product names, prices, awards, or test results.
- Fails if rankings lack criteria.
- Fails if every entry has the same wording.
- Fails if it calls the target URL the winner by default.
- Fails if it uses affiliate-style language.

{global_rules()}
""",
    )


def build_community_summary_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You are a community researcher summarizing recurring discussion "
            "patterns. You sound like someone who read many threads and is "
            "mapping what people keep asking, disputing, and leaving unresolved."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Summarize recurring themes from community discussions. This should feel
community-derived, not educational and not like a normal blog article.

Focus:
- What people keep asking.
- What people disagree on.
- What complaints recur.
- What advice keeps appearing.
- What remains unresolved.
- How the selected angle changes what matters.

Structure:
1. Start with the recurring pattern, not a category explanation.
2. Group the repeated questions or complaints into discussion clusters.
3. Show the disagreements inside the community.
4. Name the advice that keeps appearing.
5. End with what still has no satisfying answer.

Failure criteria:
- Fails if it reads like a normal blog article.
- Fails if it sounds educational.
- Fails if it does not feel community-derived.
- Fails if it invents specific users, quotes, or threads.
- Fails if it turns community signals into product promotion.

{global_rules()}
""",
    )


def build_experience_report_prompt(context: dict):
    return ContentPrompt(
        system_prompt=(
            "You write synthesized experience reports from discussion patterns. "
            "You never pretend composite observations are real users, and you "
            "clearly distinguish observed patterns from documented facts."
        ),
        user_prompt=f"""
{shared_context(context)}

Writing goal:
Create a composite experience report from discussion evidence. It must clearly
state that the observations are synthesized from discussion patterns. Do not
fabricate real users, stories, quotes, metrics, or outcomes.

Focus:
- Observed pattern.
- Representative concern.
- Competing viewpoints.
- Practical implications.
- Where the evidence does not go far enough.

Structure:
1. State that this is synthesized from recurring discussion patterns.
2. Describe the observed pattern.
3. Explain the representative concern.
4. Compare competing viewpoints.
5. Pull out practical implications without pretending they are proven outcomes.

Failure criteria:
- Fails if it becomes a case study.
- Fails if it invents real people.
- Fails if it becomes promotional.
- Fails if it claims direct first-hand use.
- Fails if it hides that the report is synthesized.

{global_rules()}
""",
    )


def build_generation_plan(evidence: dict):
    questions = []

    for fact in evidence.get("facts", []):
        questions.extend(fact.get("items", []))

    clusters = cluster_questions_by_theme(questions)

    if not clusters:
        return (
            "Extract broad category themes, group related concerns, build a "
            "content-specific outline, then write one cohesive piece."
        )

    lines = []

    for theme, items in clusters.items():
        lines.append(f"{theme}:")

        for item in items[:4]:
            lines.append(f"- {item}")

    return "\n".join(lines)


def cluster_questions_by_theme(questions: list[str]):
    theme_keywords = {
        "Decision Criteria": [
            "best",
            "worth",
            "choose",
            "recommend",
            "should",
        ],
        "Comparison And Alternatives": [
            "vs",
            "versus",
            "alternative",
            "compare",
            "better",
        ],
        "Pricing And Access": [
            "free",
            "price",
            "pricing",
            "cost",
            "paid",
        ],
        "Workflow And Use Cases": [
            "how",
            "workflow",
            "use",
            "student",
            "beginner",
        ],
        "Risk And Trust": [
            "detect",
            "safe",
            "accurate",
            "rejected",
            "mistake",
        ],
    }

    clusters = {
        theme: []
        for theme in theme_keywords
    }

    clusters["Other User Questions"] = []

    for question in questions:
        normalized = question.lower()
        matched_theme = None

        for theme, keywords in theme_keywords.items():
            if any(keyword in normalized for keyword in keywords):
                matched_theme = theme
                break

        clusters[matched_theme or "Other User Questions"].append(question)

    return {
        theme: items
        for theme, items in clusters.items()
        if items
    }


PROMPT_TEMPLATES = {
    "comparison": build_comparison_prompt,
    "review": build_review_prompt,
    "guide": build_guide_prompt,
    "discussion": build_discussion_prompt,
    "reddit_post": build_discussion_prompt,
    "blog_post": build_blog_post_prompt,
    "alternatives": build_alternatives_prompt,
    "educational": build_educational_prompt,
    "opinion": build_opinion_prompt,
    "case_study": build_case_study_prompt,
    "best_of": build_best_of_prompt,
    "community_summary": build_community_summary_prompt,
    "experience_report": build_experience_report_prompt,
    "faq_post": build_educational_prompt,
    "buying_guide": build_guide_prompt,
}

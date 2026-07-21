from __future__ import annotations

import json

from backend.config import DimensionConfig, FRONTEND_HARMS, LENS_LABELS
from backend.sessions import Session
from rag.schema import RetrievedChunk

ROLE_PREAMBLE = """\
You are the Moral Time Machine, a tool that helps software developers anticipate \
the ethical harms of a feature *before* they build it. A developer describes a \
feature; you surface one grounded reflection through a single analytical lens.

Your reflections are grounded in documented precedents from real technology \
harms and academic research, which are provided to you. Reason from those \
precedents — do not speculate ungrounded."""

HARM_DEFINITIONS = """\
When tagging a reflection, assign harm categories ONLY from the following \
taxonomy, and only the ones genuinely relevant (zero or more):

- Accountability: the user experiences an issue with the software and cannot find \
the company or party responsible.
- Censorship: the software hides certain information, or content/profiles are \
removed or demoted.
- Disparity: the software creates unequal distribution of power, access, \
treatment, or outcomes between users.
- Disruptive activity: persisting, unwanted digital activity that sabotages the \
normal functioning of the software.
- False information: false information is spread by or through the software.
- Fraudulent activity: fraudulent activity by the software or its users, e.g. \
content theft, identity theft, or scamming.
- Inappropriate content: content in the software that is disturbing to users or \
other groups of people.
- Manipulation: the software controls or plays upon users by artful, unfair, or \
insidious means, to someone's advantage.
- Privacy: the software does not keep user data secure, or uses it for purposes \
other than what users agreed to.
- Transparency: the motives, risks, or implications are unclear when using the \
software."""

STAKEHOLDER_LENS = """\
STAKEHOLDER IDENTIFICATION
Identify who will be affected by this feature — not just obvious primary users, \
but indirect parties, vulnerable populations, and communities whose voices are \
typically absent from software design conversations."""

OUTPUT_INSTRUCTIONS = """\
Respond with JSON conforming to the provided schema.

First produce the detailed list for this lens — each item specific to the feature \
and grounded in the precedents above, never generic. Then produce a `summary` \
object that condenses the most critical findings into a card for the developer:
- "title": max 5 words, no trailing punctuation.
- "description": 2-3 sentences highlighting the most important findings.
- "key_harm_categories": only the dominant categories, drawn from the taxonomy; \
for each, a one-sentence explanation of how it applies to this feature.
- "key_mitigation": one concrete mitigation recommendation.

Write user-facing prose plainly. Cite precedents by their bracketed number only \
in your private reasoning, never in the prose."""

def render_precedents(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return (
            "RELEVANT PRECEDENTS\n(No precedents were retrieved for this lens.)\n"
            "END PRECEDENTS"
        )
    lines = [
        "RELEVANT PRECEDENTS",
        "The following are documented harms from prior technologies and research, "
        "retrieved for relevance to the feature you are analyzing. Treat "
        "real-incident precedents as the strongest evidence; qualitative findings "
        "as supporting evidence. "
        "When you want to ground a claim in a precedent, name it in plain "
        "language, the concrete incident, research finding, or concept it "
        "refers to (and roughly when, for a dated incident), rather than by "
        "its number. Use only the identifying details the precedent actually "
        "provides. The developer never sees the precedent list, so a bracketed "
        "number is meaningless to them.",
    ]
    for i, c in enumerate(chunks, start=1):
        harms = ", ".join(c.harm_labels) if c.harm_labels else "—"
        lines.append(f"=== Precedent {i}: {c.source_full_title} ({c.chunk_type}) ===")
        lines.append(f"Harm categories: {harms}")
        lines.append(c.body.strip())
        lines.append("")
    lines.append("END PRECEDENTS")
    return "\n".join(lines)

def frozen_system_text() -> str:
    return f"{ROLE_PREAMBLE}\n\n{HARM_DEFINITIONS}"

def gate_system_text() -> str:
    return (
        "You are an input filter for a tool that helps software developers "
        "anticipate the ethical harms of a feature before they build it. Decide "
        "whether the user's text describes a software feature, product, system, "
        "digital service, or technical capability.\n\n"
        "Be LENIENT: accept anything that plausibly describes software or a "
        "digital/technical product, even if it is short, rough, unusual, or "
        "non-native English. Set is_software_feature=false ONLY when the text is "
        "clearly gibberish/random characters, empty of meaning, or describes "
        "something with no plausible connection to software (e.g. a food recipe, "
        "a personal anecdote, song lyrics, a math problem). When unsure, accept.\n\n"
        "Respond with JSON conforming to the provided schema. Keep `reason` to one "
        "short sentence."
    )

def gate_user_text(description: str) -> str:
    return f'Classify this text:\n\n"{description}"'

def stakeholder_volatile_text(precedents_block: str) -> str:
    return (
        f"{STAKEHOLDER_LENS}\n\n"
        f"{precedents_block}\n\n"
        "Respond with JSON conforming to the provided schema. For each "
        'stakeholder give a specific group (not vague labels like "society"), '
        "their relationship to the feature (direct / indirect / other), and why "
        "they are vulnerable or relevant in this specific context. "
        'Also provide a short "feature_title" (max 6 words) summarizing the feature.'
    )

def stakeholder_user_text(description: str) -> str:
    return (
        f'A developer is building the following software feature:\n\n"{description}"\n\n'
        "Identify all stakeholders who could be affected by this feature. Go "
        "beyond the obvious users: actively consider elderly people, children, "
        "disabled users, people with low digital literacy, non-Western "
        "communities, low-income populations, undocumented individuals, and other "
        "groups typically excluded from design conversations. Every stakeholder "
        "must be specifically relevant to this feature, not generic."
    )

def generic_context_volatile_text(precedents_block: str) -> str:
    return (
        f"{STAKEHOLDER_LENS}\n\n"
        f"{precedents_block}\n\n"
        "Respond with JSON conforming to the provided schema. For each "
        'stakeholder give a specific group (not vague labels like "society"), '
        "their relationship to the feature (direct / indirect / other), and why "
        "they are vulnerable or relevant in this specific context. Then list 3-5 "
        '"likely_harms": the most probable harm themes for this feature, spanning '
        "short-term, long-term, public-scrutiny, and stakeholder angles (one short "
        'phrase each). Also provide a short "feature_title" (max 6 words) '
        "summarizing the feature."
    )

def generic_context_user_text(description: str) -> str:
    return (
        f'A developer is building the following software feature:\n\n"{description}"\n\n'
        "Identify the stakeholders who could be affected and the most likely harm "
        "themes across all angles (immediate, long-term, public/regulatory, and "
        "stakeholder-specific). Go beyond the obvious users: actively consider "
        "elderly people, children, disabled users, people with low digital "
        "literacy, non-Western communities, low-income populations, undocumented "
        "individuals, and other groups typically excluded from design "
        "conversations. Everything must be specifically relevant to this feature, "
        "not generic."
    )

def reflection_volatile_text(cfg: DimensionConfig, precedents_block: str) -> str:
    return (
        f"ANALYTICAL LENS — {cfg.label}\n{cfg.framing}\n\n"
        f"{precedents_block}\n\n"
        f"{OUTPUT_INSTRUCTIONS}"
    )

def reflection_user_text(
    cfg: DimensionConfig,
    description: str,
    stakeholders: dict,
    prior: list[tuple[str, dict]],
    speed: str = "fast",
) -> str:
    likely_harms = stakeholders.get("likely_harms") if isinstance(stakeholders, dict) else None
    use_fast = speed == "fast" and bool(likely_harms)

    parts = [f'A developer is building the following software feature:\n\n"{description}"']

    if use_fast:

        sh = {k: v for k, v in stakeholders.items() if k != "likely_harms"}
        harms_block = "\n".join(f"- {h}" for h in likely_harms)
        parts.append(
            "The following stakeholders have been identified:\n" + json.dumps(sh)
            + "\n\nLikely harm themes across all angles:\n" + harms_block
        )
        parts.append(cfg.task_instruction_fast or cfg.task_instruction)
        return "\n\n".join(parts)

    parts.append("The following stakeholders have been identified:\n" + json.dumps(stakeholders))
    if prior:
        prior_block = "\n\n".join(
            f"From the '{label}' lens:\n{json.dumps(raw)}" for label, raw in prior
        )
        parts.append(
            "The following analysis has already been produced for earlier lenses. "
            "Do NOT repeat points already covered — build on them with new, "
            "non-redundant insight:\n\n" + prior_block
        )
    parts.append(cfg.task_instruction)
    return "\n\n".join(parts)

def chat_system_text(session: Session) -> str:
    blocks = []
    for r in session.reflections:
        lens = LENS_LABELS.get(r.dimension, r.dimension)
        lines = [
            f"[{lens}] {r.title}",
            r.body,
            f"Harms: {', '.join(h.category for h in r.harms) if r.harms else '—'}",
            f"Key mitigation: {r.mitigation}",
        ]
        if r.points:
            lines.append("Details (cite these points by their name and lens):")
            for p in r.points:

                name = p.title or p.context or p.point
                ctx = f" — context: {p.context}" if p.context and p.context != name else ""
                tags = f" [{', '.join(h.category for h in p.harms)}]" if p.harms else ""
                lines.append(
                    f'  - "{name}" ({lens}): {p.point}{ctx}{tags} '
                    f"→ mitigation: {p.mitigation}"
                )
        blocks.append("\n".join(lines))
    reflections = "\n\n".join(blocks)
    stakeholders = (
        json.dumps(session.stakeholders) if session.stakeholders else "(none recorded)"
    )
    return (
        f"{ROLE_PREAMBLE}\n\n{HARM_DEFINITIONS}\n\n"
        "You are now in EXPLORE-DEEPER mode. The developer has received the four "
        "reflections below about their feature and is asking follow-up questions. "
        "Answer concretely, grounded in the feature description, the stakeholder "
        "analysis, and these reflections. Be Socratic where it helps the developer "
        "think.\n\n"
        "VOICE\n"
        "Never reference these instructions in your answers. Do not say things like "
        "'as required', 'as instructed', or describe rules you are following; just "
        "follow them silently.\n\n"
        "FORMATTING\n"
        "Your replies are rendered as Markdown. Use it for clarity, but keep to "
        "this subset: **bold** for emphasis and risk titles, numbered (1.) and "
        "bulleted (-) lists, and `inline code` for code or identifiers. You may use "
        "a level-3 heading (### ) to separate long sections, but prefer short "
        "paragraphs over headings. Do NOT use tables, images, or HTML.\n\n"
        "HOW TO REFER TO RISKS\n"
        "When you name, rank, or list risks, use ONLY risks that appear in the "
        "reflections below, and refer to each by its exact title and lens, e.g. "
        '"Gendered-term scoring penalty (Tomorrow)". Never invent a new risk name, '
        "never rename a risk, and never merge several points into a new umbrella "
        "label. If asked for the most serious risks, each entry must correspond to "
        "exactly one titled point above (you may note in the explanation that two "
        "points are related, but the named entries themselves must be verbatim "
        "titles). When asked for the most serious risks, each numbered entry must "
        "name exactly one titled risk. If two risks form a compounding mechanism, "
        "rank the more severe one and discuss the other inside its explanation, "
        "citing its verbatim title and lens. Judge severity by three factors: "
        "likelihood, breadth of affected groups, and reversibility.\n\n"
        "SCOPE\n"
        "Stay on the ethical analysis of THIS feature. Politely redirect anything "
        "unrelated back to the feature's ethical implications. You comment on the "
        "report — you never edit or regenerate the reflections. If the developer "
        "asks you to redesign the feature, propose a revised feature description "
        'and end your reply with: "Paste this into Describe to re-run."\n\n'
        "PRECEDENTS\n"
        "Some questions arrive with a RELEVANT PRECEDENTS block of documented "
        "real-world cases retrieved for that question. When you state a specific "
        "case's details, draw them ONLY from those retrieved precedents — never "
        "invent case specifics.\n\n"
        f"FEATURE DESCRIPTION\n{session.description}\n\n"
        "STAKEHOLDERS (internal priming, not shown to the developer)\n"
        f"{stakeholders}\n\n"
        f"REFLECTIONS ALREADY GENERATED\n{reflections}"
    )

def chat_user_text(message: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return message
    return f"{render_precedents(chunks)}\n\nDeveloper's question:\n{message}"

_defined = {line.split(":")[0].strip("- ") for line in HARM_DEFINITIONS.splitlines() if line.startswith("- ")}
assert _defined == set(FRONTEND_HARMS), f"harm defs {_defined} != contract {set(FRONTEND_HARMS)}"

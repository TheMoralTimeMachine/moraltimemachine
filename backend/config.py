from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from rag.schema import SPECTRUM_LABELS

MODEL = os.getenv("MTM_MODEL", "claude-opus-4-8")

CHAT_MODEL = os.getenv("MTM_CHAT_MODEL", "claude-sonnet-4-6")
CHAT_EFFORT = os.getenv("MTM_CHAT_EFFORT", "low")

CHAT_RETRIEVAL_K = 3

CHAT_HISTORY_MAX_MESSAGES = 20

REFLECTION_EFFORT = os.getenv("MTM_EFFORT", "low")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("MTM_CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

DIMENSION_ORDER: list[str] = [
    "tomorrow",
    "in_five_years",
    "public_scrutiny",
    "stakeholder_impact",
]

LENS_LABELS: dict[str, str] = {
    "tomorrow": "Tomorrow",
    "in_five_years": "In five years",
    "public_scrutiny": "Public scrutiny",
    "stakeholder_impact": "Stakeholders",
}

FRONTEND_HARMS: list[str] = [
    "Accountability",
    "Censorship",
    "Disparity",
    "Disruptive activity",
    "False information",
    "Fraudulent activity",
    "Inappropriate content",
    "Manipulation",
    "Privacy",
    "Transparency",
]
assert set(FRONTEND_HARMS) == set(SPECTRUM_LABELS), (
    f"FRONTEND_HARMS {set(FRONTEND_HARMS)} must equal the corpus taxonomy "
    f"{set(SPECTRUM_LABELS)} (see rag/schema.py)"
)

DESCRIPTION_MIN = 10
DESCRIPTION_MAX = 4000
MESSAGE_MIN = 1
MESSAGE_MAX = 2000

LIKERT_IDS: list[str] = [f"likert_{i}" for i in range(1, 9)]
OPEN_IDS: list[str] = [f"open_{i}" for i in range(1, 6)]

NULLABLE_LIKERT_IDS: frozenset[str] = frozenset({"likert_8"})

DEMOGRAPHIC_IDS: list[str] = ["role", "experience", "ethics_familiarity", "age", "gender"]

RETRIEVAL_K = 5

GATE_MODEL = os.getenv("MTM_GATE_MODEL", "claude-haiku-4-5")

GATE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_software_feature": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["is_software_feature", "reason"],
    "additionalProperties": False,
}

OFFTOPIC_MESSAGE = (
    "No software feature detected. Please describe a software feature, system, "
    "or digital product."
)

_HARM_REF = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(FRONTEND_HARMS)},
        "explanation": {"type": "string"},
    },
    "required": ["category", "explanation"],
    "additionalProperties": False,
}

_HARM_ARRAY = {"type": "array", "items": _HARM_REF}

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "key_harm_categories": _HARM_ARRAY,
        "key_mitigation": {"type": "string"},
    },
    "required": ["title", "description", "key_harm_categories", "key_mitigation"],
    "additionalProperties": False,
}

_HARM_ITEM = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "harm": {"type": "string"},
        "affected_stakeholders": {"type": "array", "items": {"type": "string"}},
        "harm_categories": _HARM_ARRAY,
        "mitigation": {"type": "string"},
    },
    "required": ["title", "harm", "affected_stakeholders", "harm_categories", "mitigation"],
    "additionalProperties": False,
}
_CONCERN_ITEM = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "concern": {"type": "string"},
        "who_raises_it": {"type": "string"},
        "framing": {"type": "string"},
        "harm_categories": _HARM_ARRAY,
        "mitigation": {"type": "string"},
    },
    "required": ["title", "concern", "who_raises_it", "framing", "harm_categories", "mitigation"],
    "additionalProperties": False,
}
_IMPACT_ITEM = {
    "type": "object",
    "properties": {
        "stakeholder": {"type": "string"},
        "impact": {"type": "string"},
        "harm_categories": _HARM_ARRAY,
        "mitigation": {"type": "string"},
    },
    "required": ["stakeholder", "impact", "harm_categories", "mitigation"],
    "additionalProperties": False,
}

STAKEHOLDER_MODEL = os.getenv("MTM_STAKEHOLDER_MODEL", "claude-haiku-4-5")
STAKEHOLDER_QUERY_AUGMENT = ""
STAKEHOLDER_CHUNK_TYPES: tuple[str, ...] = ("real-incident",)

STAKEHOLDER_SCHEMA = {
    "type": "object",
    "properties": {
        "feature_title": {"type": "string"},
        "stakeholders": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "group": {"type": "string"},
                    "relationship": {"type": "string", "enum": ["direct", "indirect", "other"]},
                    "relevance": {"type": "string"},
                },
                "required": ["group", "relationship", "relevance"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["feature_title", "stakeholders"],
    "additionalProperties": False,
}

GENERIC_CONTEXT_QUERY_AUGMENT = ""
GENERIC_CONTEXT_CHUNK_TYPES: tuple[str, ...] | None = None

GENERIC_CONTEXT_SCHEMA = {
    "type": "object",
    "properties": {
        "feature_title": {"type": "string"},
        "stakeholders": STAKEHOLDER_SCHEMA["properties"]["stakeholders"],
        "likely_harms": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["feature_title", "stakeholders", "likely_harms"],
    "additionalProperties": False,
}

@dataclass(frozen=True)
class DimensionConfig:

    label: str

    framing: str

    query_augment: str

    chunk_types: tuple[str, ...] | None

    task_instruction: str

    item_key: str

    item_schema: dict[str, Any]

    task_instruction_fast: str | None = None

RETRIEVAL_BY_DIMENSION: dict[str, DimensionConfig] = {
    "tomorrow": DimensionConfig(
        label="Tomorrow",
        framing=(
            "Immediate, short-term harms that could surface as soon as the "
            "feature ships — day-one effects on real users."
        ),
        query_augment=" short-term immediate harms",
        chunk_types=None,
        task_instruction=(
            "Identify short-term ethical harms that could realistically occur on "
            "or shortly after launch. For each harm, give: a short title (max 5 "
            "words, no trailing punctuation) naming the harm, the specific harm "
            "(not vague), which stakeholder(s) are affected, which harm categories "
            "apply — and for each category one sentence on how it applies to THIS "
            "feature — and a concrete mitigation the developer could implement. "
            "Stay focused on immediate consequences — do not drift into long-term "
            "systemic effects."
        ),
        item_key="harms",
        item_schema=_HARM_ITEM,
    ),
    "in_five_years": DimensionConfig(
        label="In Five Years",
        framing=(
            "Long-term, systemic, second-order consequences that compound "
            "quietly over years before anyone notices the drift."
        ),
        query_augment=" long-term systemic consequences",
        chunk_types=None,
        task_instruction=(
            "Identify long-term ethical harms that could emerge over months or "
            "years of widespread use. Think about feedback loops, normalization "
            "effects, market-level shifts, cumulative impact on vulnerable groups, "
            "and second-order consequences the developer would not anticipate "
            "today. Do not repeat harms already covered in the short-term "
            "analysis — build on them: how do they compound, evolve, or create new "
            "problems over time? For each harm, give: a short title (max 5 words, "
            "no trailing punctuation) naming the harm, the specific harm, which "
            "stakeholder(s) are affected, which harm categories apply — and for "
            "each category one sentence on how it applies to THIS feature — and a "
            "concrete mitigation."
        ),
        task_instruction_fast=(
            "Building on the likely harm themes in the shared context above, "
            "identify long-term ethical harms that could emerge over months or "
            "years of widespread use: how those themes compound, normalize, "
            "create feedback loops, drive market-level shifts, or produce "
            "second-order consequences for vulnerable groups that the developer "
            "would not anticipate today. For each harm, give: a short title (max "
            "5 words, no trailing punctuation) naming the harm, the specific "
            "harm, which stakeholder(s) are affected, which harm categories "
            "apply, and for each category one sentence on how it applies to THIS "
            "feature, and a concrete mitigation."
        ),
        item_key="harms",
        item_schema=_HARM_ITEM,
    ),
    "public_scrutiny": DimensionConfig(
        label="Public Scrutiny",
        framing=(
            "How regulators, journalists, and the public would judge this "
            "feature — reputational, legal, and audit exposure. Be adversarial: "
            "write as if preparing to expose this feature, not defend it."
        ),
        query_augment=" regulatory media scrutiny",
        chunk_types=("real-incident",),
        task_instruction=(
            "Analyze this feature from the perspective of external scrutiny: how "
            "outsiders (journalists, regulators, advocacy groups, affected "
            "communities) would react if this feature and its consequences became "
            "public knowledge. Do not repeat harms already covered; focus on how "
            "this feature would be perceived, framed, and acted upon by external "
            "parties. For each concern, give: a short title (max 5 words, no "
            "trailing punctuation) naming the concern, what would be flagged, who "
            "would raise it (be specific, e.g. EU data protection authorities), how they "
            "would frame it publicly (the headline / complaint / campaign angle), "
            "which harm categories apply — and for each category one sentence on "
            "how it applies to THIS feature — and a concrete mitigation the "
            "developer could implement before this becomes public."
        ),
        task_instruction_fast=(
            "Analyze this feature from the perspective of external scrutiny: how "
            "outsiders (journalists, regulators, advocacy groups, affected "
            "communities) would react if this feature and its consequences became "
            "public knowledge. The other lenses cover immediate and long-term "
            "harms and stakeholder impact; focus on what is distinctive to "
            "external scrutiny — how outsiders would perceive, frame, and act on "
            "this feature. For each concern, give: a short title (max 5 words, no "
            "trailing punctuation) naming the concern, what would be flagged, who "
            "would raise it (be specific, e.g. EU data protection authorities), how they "
            "would frame it publicly (the headline / complaint / campaign angle), "
            "which harm categories apply — and for each category one sentence on "
            "how it applies to THIS feature — and a concrete mitigation the "
            "developer could implement before this becomes public."
        ),
        item_key="concerns",
        item_schema=_CONCERN_ITEM,
    ),
    "stakeholder_impact": DimensionConfig(
        label="Stakeholders",
        framing=(
            "The people affected — especially those with no direct relationship "
            "to the deploying organization — and how they experience the harm."
        ),
        query_augment="",
        chunk_types=("qualitative-finding",),
        task_instruction=(
            "Go deeper on stakeholder impact. For each stakeholder identified "
            "above, analyze: how this feature specifically affects them (based on "
            "their circumstances, not generically), what harms are unique to them "
            "that have not been surfaced yet, and a concrete mitigation tailored to "
            "their situation. Pay special attention to stakeholders who are "
            "marginalized, underrepresented, or typically ignored in software "
            "design: elderly users, disabled users, low-income populations, "
            "non-Western communities, children, digitally illiterate users, "
            "undocumented individuals. Do not rehash harms already covered — add "
            "new perspective, not repetition. For each impact, also tag which harm "
            "categories apply, with one sentence per category on how it applies to "
            "this stakeholder."
        ),
        task_instruction_fast=(
            "Go deeper on stakeholder impact. For each stakeholder identified "
            "above, analyze: how this feature specifically affects them (based on "
            "their circumstances, not generically), what harms are unique to them "
            "beyond the shared harm themes above, and a concrete mitigation tailored to "
            "their situation. Pay special attention to stakeholders who are "
            "marginalized, underrepresented, or typically ignored in software "
            "design: elderly users, disabled users, low-income populations, "
            "non-Western communities, children, digitally illiterate users, "
            "undocumented individuals. The other lenses cover harms in general "
            "terms; here focus on how each specific stakeholder experiences them "
            "and what is unique to their circumstances. For each impact, also tag "
            "which harm categories apply, with one sentence per category on how it "
            "applies to this stakeholder."
        ),
        item_key="stakeholder_impacts",
        item_schema=_IMPACT_ITEM,
    ),
}

def response_schema(cfg: DimensionConfig) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            cfg.item_key: {"type": "array", "items": cfg.item_schema},
            "summary": SUMMARY_SCHEMA,
        },
        "required": [cfg.item_key, "summary"],
        "additionalProperties": False,
    }

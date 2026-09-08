"""Deterministic intent, language and lightweight game-context extraction."""

from __future__ import annotations

import re
from typing import Literal


Intent = Literal[
    "greeting",
    "fact_lookup",
    "how_to",
    "recommendation",
    "comparison",
    "event",
    "troubleshooting",
    "unclear",
    "out_of_scope",
]


_GREETING = re.compile(
    r"^\s*(bonjour|bonsoir|salut|merci|au revoir|hello|hi|hey|thanks|bye|السلام عليكم|مرحبا|شكرا)[!. ]*$",
    re.IGNORECASE,
)
_AUTOMATION = re.compile(
    r"\b(bot|macro|autoclick|auto[- ]?farm|automatis(?:er|ation)|pirat|hack|cheat|triche|تحكم تلقائي)\b",
    re.IGNORECASE,
)
_LEGACY_SCOPE = re.compile(
    r"\b(qos|packet loss|latency|jitter|throughput|mininet|openflow|sla réseau|network routing)\b",
    re.IGNORECASE,
)

_TOPICS: dict[str, tuple[str, ...]] = {
    "heroes": ("héros", "hero", "heroes", "بطل", "أبطال"),
    "monster-hunt": ("chasse", "monstre", "monster hunt", "hunting", "صيد", "وحش"),
    "darknests": ("sombre nid", "sombres nids", "darknest", "dark nest", "العش"),
    "jewels": ("joyau", "joyaux", "jewel", "gem", "جوهرة"),
    "equipment": ("équipement", "equipement", "equipment", "gear", "عتاد"),
    "troops": ("troupe", "infanterie", "cavalerie", "distance", "troop", "infantry", "cavalry", "ranged", "قوات"),
    "events": ("événement", "evenement", "event", "arène du dragon", "dragon arena", "حدث"),
    "buildings": ("bâtiment", "batiment", "château", "chateau", "building", "castle", "مبنى", "قلعة"),
    "research": ("recherche", "research", "academy", "académie", "بحث", "أكاديمية"),
}


def detect_language(text: str, requested: str | None = None) -> str:
    if requested:
        return requested
    if re.search(r"[\u0600-\u06ff]", text):
        return "ar"
    if re.search(r"\b(the|what|which|how|should|best|with|for)\b", text, re.IGNORECASE):
        return "en"
    return "fr"


def classify_intent(text: str) -> Intent:
    query = text.strip()
    lowered = query.lower()
    if not query or _GREETING.match(query):
        return "greeting" if query else "unclear"
    if _AUTOMATION.search(query) or _LEGACY_SCOPE.search(query):
        return "out_of_scope"
    if len(query.split()) < 3 and not any(
        keyword in lowered for keywords in _TOPICS.values() for keyword in keywords
    ):
        return "unclear"
    if re.search(r"\b(compare|compar|différence|difference|versus|\bvs\b|مقارنة)\b", lowered):
        return "comparison"
    if re.search(r"\b(meilleur|best|recommend|conseil|choisir|devrais|أفضل|أنصح)\b", lowered):
        return "recommendation"
    if re.search(r"\b(event|événement|evenement|arena|arène|kvk|guild fest|حدث)\b", lowered):
        return "event"
    if re.search(r"\b(comment|how to|étapes|etapes|procédure|procedure|كيف)\b", lowered):
        return "how_to"
    if re.search(r"\b(échoue|echoue|problème|probleme|ne marche pas|fail|issue|مشكلة)\b", lowered):
        return "troubleshooting"
    return "fact_lookup"


def extract_topics(text: str) -> list[str]:
    lowered = text.lower()
    return [
        topic
        for topic, keywords in _TOPICS.items()
        if any(keyword in lowered for keyword in keywords)
    ]


def extract_game_version(text: str, requested: str | None = None) -> str | None:
    if requested:
        return requested
    match = re.search(r"\b(?:version|v)\s*(\d+(?:\.\d+){1,2})\b", text, re.IGNORECASE)
    return match.group(1) if match else None


def needs_clarification(text: str, intent: Intent, player_context: dict | None = None) -> bool:
    if intent == "unclear":
        return True
    if intent == "recommendation":
        lowered = text.lower()
        has_subject = bool(extract_topics(text))
        has_goal = any(
            term in lowered
            for term in ("attaque", "défense", "defense", "chasse", "construction", "recherche", "attack", "defend", "hunt")
        )
        return not has_subject or (not has_goal and not player_context)
    return False


def rewrite_queries(text: str, topics: list[str]) -> list[str]:
    """Add official names and bilingual synonyms without changing intent."""
    expansions = {
        "heroes": "héros Heroes bonus armée infanterie cavalerie distance",
        "monster-hunt": "chasse aux monstres Monster Hunt héros dégâts physiques magiques",
        "darknests": "Sombres nids Darknests ralliement reconnaissance contres de troupes",
        "jewels": "joyaux Jewels grades fusion sertissage bonus de combat",
        "equipment": "équipement Equipment sets construction recherche combat",
        "troops": "troupes infantry ranged cavalry infanterie distance cavalerie",
        "events": "événements Lords Mobile règles récompenses version",
        "buildings": "bâtiments château prérequis progression",
        "research": "recherche Académie prérequis progression",
    }
    alternatives = [f"{text} {expansions[topic]}" for topic in topics if topic in expansions]
    return list(dict.fromkeys(alternatives))[:2]

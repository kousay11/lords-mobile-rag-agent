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
_BROAD_BATTLE_REQUEST = re.compile(
    r"\b(?:"
    r"toutes?\s+les\s+(?:batailles|combats)|tous\s+les\s+combats|"
    r"toujours\s+gagner|garantir\w*\s+(?:la\s+)?victoire|"
    r"(?:être|etre)\s+vainqueur\w*\s+(?:dans|de)\s+tout|"
    r"every\s+battle|all\s+battles|always\s+win|guarantee\w*\s+(?:a\s+)?win|"
    r"الفوز\s+في\s+كل|أضمن\s+الفوز"
    r")\b",
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
    if requested in {"fr", "en", "ar"}:
        return requested
    if re.search(r"[\u0600-\u06ff]", text):
        return "ar"
    if re.search(
        r"[àâçéèêëîïôùûüÿœ]|\b(?:bonjour|salut|comment|quel(?:le)?s?|je|mon|ma|mes|"
        r"pour|avec|dans|gagner|bataille|combat|troupe|héros|royaume)\b",
        text,
        re.IGNORECASE,
    ):
        return "fr"
    if re.search(
        r"\b(?:hello|hi|the|what|which|how|should|best|with|for|win|battle|troop|hero)\b",
        text,
        re.IGNORECASE,
    ):
        return "en"
    return requested if requested in {"fr", "en", "ar"} else "fr"


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


def needs_clarification(text: str, intent: Intent, player_context: dict | None = None) -> bool:
    if intent == "unclear":
        return True
    if _BROAD_BATTLE_REQUEST.search(text):
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


def rewrite_queries(
    text: str, topics: list[str], player_context: dict | None = None
) -> list[str]:
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
    # Biaise la récupération vers le profil : niveau, style et contexte
    # complémentaire deviennent des termes de requête (jamais des instructions).
    profile_terms: list[str] = []
    player = player_context or {}
    level = str(player.get("level") or "").strip()
    if level:
        profile_terms.append(level)
    play_style = str(player.get("play_style") or "").strip()
    if play_style:
        profile_terms.append(play_style.replace("_", " "))
    for key, value in player.items():
        if key in {"response_length", "level", "play_style"}:
            continue
        if isinstance(value, str) and value.strip():
            profile_terms.append(value.strip()[:80])
        elif isinstance(value, (int, float)):
            profile_terms.append(str(value))
    if profile_terms:
        alternatives.append(f"{text} {' '.join(profile_terms)}")
    return list(dict.fromkeys(alternatives))[:3]

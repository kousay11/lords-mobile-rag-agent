import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from langchain_core.messages import HumanMessage

import graph


def _chunk(document_id="doc-1", score=0.8, status="active"):
    return {
        "text": "Le document indique une règle Lords Mobile vérifiable.",
        "score": score,
        "metadata": {
            "chunk_id": f"{document_id}-chunk",
            "document_id": document_id,
            "title": "Guide officiel",
            "url": "https://example.test/guide",
            "source_type": "official",
            "language": "fr",
            "status": status,
            "reliability": 4,
        },
    }


class GraphNodeTests(unittest.TestCase):
    def test_direct_greeting_is_read_only_and_has_no_sources(self):
        state = {"messages": [HumanMessage(content="Bonjour")]}
        classified = graph.classify_node(state)
        answer = graph.direct_answer_node({**state, **classified})
        self.assertEqual(classified["intent"], "greeting")
        self.assertEqual(answer["sources"], [])
        self.assertEqual(answer["generation_mode"], "deterministic")

    def test_context_validation_preserves_citation_order(self):
        result = graph.validate_context_node(
            {"retrieved_documents": [_chunk(score=0.9), _chunk(score=0.7)]}
        )
        self.assertEqual(len(result["sources"]), 2)
        self.assertEqual(
            result["sources"][0]["content"],
            "Le document indique une règle Lords Mobile vérifiable.",
        )
        self.assertGreater(result["confidence"], 0)
        self.assertFalse(result["needs_clarification"])

    def test_broad_battle_question_returns_deterministic_clarification(self):
        state = {
            "messages": [
                HumanMessage(
                    content="Explique comment gagner toutes les batailles du jeu."
                )
            ],
            "language": "en",
        }
        classified = graph.classify_node(state)
        extracted = graph.extract_game_context_node({**state, **classified})
        answer = graph.clarification_answer_node({**state, **classified, **extracted})
        self.assertEqual(classified["language"], "en")
        self.assertTrue(extracted["needs_clarification"])
        self.assertEqual(
            graph.route_after_context_extraction(extracted), "clarification_answer"
        )
        self.assertEqual(answer["generation_mode"], "deterministic_clarification")
        self.assertIn("guarantee", answer["messages"][0].content)

    def test_saved_language_wins_over_question_language(self):
        state = {
            "messages": [HumanMessage(content="Conseille-moi sur les héros")],
            "language": "en",
        }
        self.assertEqual(graph.classify_node(state)["language"], "en")

    def test_grounding_validator_rejects_unsupported_percentage_and_name(self):
        issues = graph.grounding_issues(
            'Utilisez 40–50 % d’infanterie avec “Berserker”. [1]', [_chunk()]
        )
        self.assertTrue(any(item.startswith("unsupported_percentage") for item in issues))
        self.assertTrue(any(item.startswith("unsupported_quoted_term") for item in issues))

    def test_grounding_validator_accepts_supported_claim(self):
        chunk = _chunk()
        chunk["text"] = "Le guide recommande exactement 50 % dans cet exemple."
        self.assertEqual(
            graph.grounding_issues("Le guide recommande 50 %. [1]", [chunk]), []
        )

    def test_empty_context_forces_safe_clarification(self):
        result = graph.validate_context_node({"retrieved_documents": []})
        self.assertEqual(result["confidence"], 0.0)
        self.assertTrue(result["needs_clarification"])

    def test_retrieval_searches_all_statuses_without_version_filter(self):
        async def run():
            mock = AsyncMock(return_value=[_chunk()])
            with patch("graph._retrieve_one", mock):
                result = await graph.retrieve_node(
                    {
                        "messages": [HumanMessage(content="Quels joyaux choisir ?")],
                        "rewritten_queries": [],
                        "player_context": {"response_length": "detailed"},
                    },
                    {"configurable": {}},
                )
            self.assertEqual(len(result["retrieved_documents"]), 1)
            self.assertEqual(
                mock.await_args.kwargs["statuses"], ["active", "deprecated", "needs_review"]
            )

        asyncio.run(run())

    def test_retrieval_truncates_to_response_length(self):
        async def run():
            mock = AsyncMock(
                return_value=[_chunk(document_id=f"doc-{i}") for i in range(8)]
            )
            with patch("graph._retrieve_one", mock):
                short = await graph.retrieve_node(
                    {
                        "messages": [HumanMessage(content="Quels joyaux choisir ?")],
                        "rewritten_queries": [],
                        "player_context": {"response_length": "short"},
                    },
                    {"configurable": {}},
                )
                standard = await graph.retrieve_node(
                    {
                        "messages": [HumanMessage(content="Quels joyaux choisir ?")],
                        "rewritten_queries": [],
                        "player_context": {"response_length": "standard"},
                    },
                    {"configurable": {}},
                )
                detailed = await graph.retrieve_node(
                    {
                        "messages": [HumanMessage(content="Quels joyaux choisir ?")],
                        "rewritten_queries": [],
                        "player_context": {"response_length": "detailed"},
                    },
                    {"configurable": {}},
                )
            self.assertEqual(len(short["retrieved_documents"]), 3)
            self.assertEqual(len(standard["retrieved_documents"]), 5)
            self.assertEqual(len(detailed["retrieved_documents"]), 8)

        asyncio.run(run())

    def test_retrieval_does_not_filter_by_answer_language(self):
        async def run():
            response = unittest.mock.Mock()
            response.json.return_value = {"chunks": [_chunk()]}
            client = AsyncMock()
            client.post.return_value = response
            client.__aenter__.return_value = client
            with patch("graph.httpx.AsyncClient", return_value=client):
                await graph._retrieve_one("Colosseum", search_type="hybrid", top_k=8,
                    statuses=["active", "deprecated", "needs_review"], min_reliability=3, min_score=0.25)
            payload = client.post.call_args.kwargs["json"]
            self.assertNotIn("language", payload)
            self.assertNotIn("game_version", payload)
            self.assertEqual(payload["statuses"], ["active", "deprecated", "needs_review"])
        asyncio.run(run())

    def test_length_and_profile_are_in_prompt_and_fallback(self):
        from prompts import build_grounded_prompt
        chunk = _chunk()
        chunk["text"] = "Une preuve. " * 100
        for length, expected in [("short", "80 à 150"), ("standard", "150 à 350"), ("detailed", "350 à 700")]:
            prompt = build_grounded_prompt(language="ar", intent="fact_lookup",
                player_context={"response_length": length}, context_blocks=[chunk])
            self.assertIn(expected, prompt)
            self.assertIn("LANGUE DE SORTIE OBLIGATOIRE: ar", prompt)
        prompt = build_grounded_prompt(language="fr", intent="fact_lookup",
            player_context={"response_length": "standard", "level": "Château 25", "play_style": "free_to_play"},
            context_blocks=[chunk])
        self.assertIn("Château 25", prompt)
        self.assertIn("free_to_play", prompt)
        short_prompt = build_grounded_prompt(language="fr", intent="fact_lookup",
            player_context={"response_length": "short"}, context_blocks=[chunk])
        self.assertIn("1 à 3", short_prompt)
        detailed_prompt = build_grounded_prompt(language="fr", intent="fact_lookup",
            player_context={"response_length": "detailed"}, context_blocks=[chunk])
        self.assertIn("3 à 8", detailed_prompt)
        short = graph._fallback_grounded_answer({"language": "fr", "player_context": {"response_length":"short"}, "retrieved_documents":[chunk]*3})
        detailed = graph._fallback_grounded_answer({"language": "fr", "player_context": {"response_length":"detailed"}, "retrieved_documents":[chunk]*3})
        self.assertLess(len(short), len(detailed))
        self.assertNotIn("[2]", short)
        self.assertIn("[3]", detailed)

    def test_needs_review_sources_warn_without_version_filter(self):
        async def run():
            mock = AsyncMock(return_value=[_chunk(status="needs_review")])
            with patch("graph._retrieve_one", mock):
                await graph.retrieve_node({"messages": [HumanMessage(content="Colosseum")],
                    "rewritten_queries": []}, {"configurable": {}})
            self.assertEqual(
                mock.await_args.kwargs["statuses"], ["active", "deprecated", "needs_review"]
            )
            with patch("graph.get_llm", side_effect=RuntimeError("offline")):
                result = await graph.generate_node({"language":"fr", "messages": [],
                    "retrieved_documents": [_chunk(status="needs_review")]}, {"configurable":{}})
            self.assertIn("Sources avec réserves", result["messages"][0].content)
        asyncio.run(run())

    def test_no_evidence_uses_fallback_without_llm(self):
        result = asyncio.run(
            graph.generate_node(
                {"language": "fr", "retrieved_documents": [], "messages": []},
                {"configurable": {}},
            )
        )
        self.assertEqual(result["generation_mode"], "safe_fallback")
        self.assertIn("preuve", result["messages"][0].content)

    def test_english_fallback_does_not_copy_foreign_source_text(self):
        result = asyncio.run(
            graph.generate_node(
                {
                    "language": "en",
                    "player_context": {"response_length": "standard"},
                    "retrieved_documents": [
                        {"text": "Pour progresser, développez Économie.", "metadata": {}}
                    ],
                    "messages": [],
                },
                {"configurable": {}},
            )
        )
        self.assertIn("The available documents", result["messages"][0].content)
        self.assertNotIn("Pour progresser", result["messages"][0].content)


if __name__ == "__main__":
    unittest.main()

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
            "game_version": "official-guide-2019-04-15",
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

    def test_context_validation_deduplicates_sources(self):
        result = graph.validate_context_node(
            {"retrieved_documents": [_chunk(score=0.9), _chunk(score=0.7)]}
        )
        self.assertEqual(len(result["sources"]), 1)
        self.assertGreater(result["confidence"], 0)
        self.assertFalse(result["needs_clarification"])

    def test_empty_context_forces_safe_clarification(self):
        result = graph.validate_context_node({"retrieved_documents": []})
        self.assertEqual(result["confidence"], 0.0)
        self.assertTrue(result["needs_clarification"])

    def test_retrieval_defaults_to_active_sources(self):
        async def run():
            mock = AsyncMock(return_value=[_chunk()])
            with patch("graph._retrieve_one", mock):
                result = await graph.retrieve_node(
                    {
                        "messages": [HumanMessage(content="Quels joyaux choisir ?")],
                        "rewritten_queries": [],
                    },
                    {"configurable": {}},
                )
            self.assertEqual(len(result["retrieved_documents"]), 1)
            self.assertEqual(mock.await_args.kwargs["statuses"], ["active"])

        asyncio.run(run())

    def test_historical_version_allows_deprecated_sources(self):
        async def run():
            mock = AsyncMock(return_value=[_chunk(status="deprecated")])
            with patch("graph._retrieve_one", mock):
                await graph.retrieve_node(
                    {
                        "messages": [HumanMessage(content="Que contient la version 2.18 ?")],
                        "game_version": "2.18",
                        "rewritten_queries": [],
                    },
                    {"configurable": {}},
                )
            self.assertEqual(
                mock.await_args.kwargs["statuses"], ["active", "deprecated"]
            )

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


if __name__ == "__main__":
    unittest.main()

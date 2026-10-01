"""Exercise /chat through the real graph, with HTTP RAG and LLM doubles only."""
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import graph
import main


class ChatRetrievalTests(unittest.TestCase):
    def run_chat(self, **request_overrides):
        chunk = {
            'text': 'When a quest is claimed or removed, a new one will appear 15 minutes later.',
            'score': 0.9,
            'metadata': {
                'source': 'wiki-guildfest', 'document_id': 'guildfest-fixture',
                'chunk_id': 'guildfest-fixture-1', 'status': 'active', 'reliability': 3,
            },
        }
        payloads = []

        async def retrieve(url, *, json):
            self.assertEqual(url, f'{graph.RAG_URL}/retrieve')
            payloads.append(json)
            # Emulate RAG metadata filtering, not retrieval or ranking quality.
            eligible = (chunk['metadata']['reliability'] >= json['min_reliability']
                        and chunk['metadata']['status'] in json['statuses'])
            response = Mock()
            response.json.return_value = {'chunks': [chunk] if eligible else []}
            return response

        rag_client = AsyncMock()
        rag_client.__aenter__.return_value = rag_client
        rag_client.post.side_effect = retrieve
        llm = Mock()
        llm.ainvoke = AsyncMock(return_value=AIMessage(content='A new quest appears 15 minutes later. [1]'))
        # No lifespan: do not initialize PostgreSQL or the production checkpointer.
        with (
            patch.object(main.app.state, 'graph', graph.build_graph(), create=True),
            patch.object(main.app.state, 'persistence_enabled', False, create=True),
            patch.object(main, '_upsert_thread', new=AsyncMock()),
            patch.object(main, '_resolve_provider', return_value=('test', 'http://llm.invalid/v1', None)),
            patch.object(main.rag_trace, 'begin', return_value=None),
            patch('graph.httpx.AsyncClient', return_value=rag_client),
            patch('graph.get_llm', return_value=llm),
        ):
            response = TestClient(main.app).post('/chat', json={
                'message': 'How do Guild Fest quests work, and what happens when a quest is deleted?',
                'language': 'en',
                **request_overrides,
            })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json(), payloads, llm

    def test_chat_default_sends_min_reliability_three_and_keeps_active_three(self):
        response, payloads, llm = self.run_chat()
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]['min_reliability'], 3)
        self.assertEqual(payloads[0]['min_relevance_score'], 0.25)
        self.assertEqual(payloads[0]['statuses'], ['active', 'deprecated', 'needs_review'])
        self.assertEqual(response['sources'][0]['document_id'], 'guildfest-fixture')
        self.assertEqual(response['sources'][0]['status'], 'active')
        self.assertEqual(response['sources'][0]['reliability'], 3)
        self.assertIn('When a quest is claimed or removed', llm.ainvoke.await_args.args[0][0].content)

    def test_chat_explicit_min_reliability_four_is_still_respected(self):
        response, payloads, llm = self.run_chat(min_reliability=4)
        self.assertEqual(payloads[0]['min_reliability'], 4)
        self.assertEqual(response['sources'], [])
        llm.ainvoke.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()

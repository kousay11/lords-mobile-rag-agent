import asyncio
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, Mock, patch

from langchain_core.messages import AIMessage, HumanMessage
import graph

FIXTURES = Path(__file__).parent / 'fixtures'
CHUNKS = json.loads((FIXTURES / 'guildfest_grounding.json').read_text())['chunks']
DRAFT = (FIXTURES / 'guildfest_point_tally_draft.txt').read_text().strip()
UNSUPPORTED = 'The guild’s total point tally remains unchanged until a quest is actually completed'
REPAIRED = ('The guild earns points by completing Guild Fest quests. [2] '
            'Rank 4 and 5 members can remove unclaimed quests without losing points or attempts. '
            'A new quest appears 15 minutes after a quest is claimed or removed. [7]')


class PointTallyGroundingTests(unittest.TestCase):
    def test_completion_scoring_is_supported_by_source_two(self):
        self.assertIn('score points, by completing Guild Fest Quests', CHUNKS[1]['text'])
        self.assertEqual(graph.grounding_issues('The guild earns the points once the quest is completed. [2]', CHUNKS), [])

    def test_no_loss_on_removal_does_not_support_global_score_invariance(self):
        for claim in (UNSUPPORTED, 'The guild score stays unchanged until a quest is completed',
                      'The guild points do not change until a quest is completed'):
            with self.subTest(claim=claim):
                issues = graph.grounding_issues(claim + '. [2] [7]', CHUNKS)
                self.assertEqual(len(issues), 1)
                self.assertTrue(issues[0].startswith('unsupported_point_tally_invariance:'))

    def test_explicit_documentary_evidence_allows_invariance(self):
        chunks = copy.deepcopy(CHUNKS)
        chunks.append({'text': UNSUPPORTED + '.', 'metadata': {'status': 'active'}})
        self.assertEqual(graph.grounding_issues(UNSUPPORTED + '. [9]', chunks), [])

    def test_actual_draft_triggers_existing_repair_and_preserves_supported_facts(self):
        issues = graph.grounding_issues(DRAFT, CHUNKS)
        self.assertEqual(len(issues), 1)
        self.assertTrue(issues[0].startswith('unsupported_point_tally_invariance:'))
        llm = Mock()
        llm.ainvoke = AsyncMock(side_effect=[AIMessage(content=DRAFT), AIMessage(content=REPAIRED)])
        state = {'messages': [HumanMessage(content='How do Guild Fest quests work, and what happens when a quest is deleted?')],
                 'language': 'en', 'retrieved_documents': copy.deepcopy(CHUNKS)}
        state.update(graph.validate_context_node(state))
        with patch('graph.get_llm', return_value=llm):
            result = asyncio.run(graph.generate_node(state, {'configurable': {}}))
        self.assertEqual(llm.ainvoke.await_count, 2)
        self.assertIn(issues[0], llm.ainvoke.await_args.args[0][-1].content)
        self.assertEqual(result['generation_mode'], 'llm_repaired')
        self.assertEqual(result['messages'][0].content, REPAIRED)
        self.assertEqual(state['retrieved_documents'], CHUNKS)

    def test_still_unsupported_repair_is_rejected(self):
        llm = Mock()
        llm.ainvoke = AsyncMock(return_value=AIMessage(content=DRAFT))
        with patch('graph.get_llm', return_value=llm):
            result = asyncio.run(graph.generate_node({'messages': [], 'language': 'en',
                'retrieved_documents': copy.deepcopy(CHUNKS)}, {'configurable': {}}))
        self.assertEqual(llm.ainvoke.await_count, 2)
        self.assertEqual(result['generation_mode'], 'grounding_fallback')
        self.assertNotIn(UNSUPPORTED, result['messages'][0].content)

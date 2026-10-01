import asyncio
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, Mock, patch

from langchain_core.messages import AIMessage, HumanMessage
import graph

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/guildfest_grounding.json').read_text())
VALID = ('Guild Fest is a 7 day event where guilds complete quests for points. [2] '
         'Rank 4 and 5 members can remove unclaimed quests without losing points or attempts. '
         'A replacement appears 15 minutes after a quest is claimed or removed. [7] '
         'The supplied context does not establish the effect of abandoning or canceling a quest.')


class GroundingRepairTests(unittest.TestCase):
    def generate(self, outputs):
        chunks = copy.deepcopy(FIXTURE['chunks'])
        llm = Mock()
        llm.ainvoke = AsyncMock(side_effect=outputs)
        state = {'messages': [HumanMessage(content='How do Guild Fest quests work, and what happens when a quest is deleted?')],
                 'language': 'en', 'player_context': {'response_length': 'detailed'},
                 'retrieved_documents': chunks}
        state.update(graph.validate_context_node(state))
        with patch('graph.get_llm', return_value=llm):
            result = asyncio.run(graph.generate_node(state, {'configurable': {}}))
        self.assertEqual(chunks, FIXTURE['chunks'])
        return result, llm

    def test_observed_draft_is_repaired_once_with_identical_context(self):
        self.assertEqual(graph.grounding_issues(FIXTURE['draft'], FIXTURE['chunks']), FIXTURE['issues'])
        result, llm = self.generate([AIMessage(content=FIXTURE['draft']), AIMessage(content=VALID)])
        self.assertEqual(llm.ainvoke.await_count, 2)
        original, repair = [call.args[0] for call in llm.ainvoke.await_args_list]
        self.assertEqual(original[0].content, repair[0].content)
        self.assertEqual(original[1:], repair[1:-1])
        for issue in FIXTURE['issues']:
            self.assertIn(issue, repair[-1].content)
        self.assertIn('Remove every unsupported claim', repair[-1].content)
        self.assertIn('paraphrase without quotation marks', repair[-1].content)
        self.assertIn('Do not infer missing rules about abandoning or canceling quests', repair[-1].content)
        self.assertEqual(result['generation_mode'], 'llm_repaired')
        self.assertIn('15 minutes', result['messages'][0].content)
        self.assertIn('[7]', result['messages'][0].content)
        self.assertNotIn('guild earns the points', result['messages'][0].content)
        self.assertNotIn('will not restore a quest attempt', result['messages'][0].content)
        self.assertEqual(result['messages'][0].additional_kwargs['metadata']['sources'][6]['chunk_id'], '285ae1ec-eb35-56e4-832a-dd1a39dbffa4')

    def test_invalid_repair_keeps_fallback_without_third_attempt(self):
        for invalid in (FIXTURE['draft'], '15 minutes [99]', '50% bonus [7]', 'No citation', 'Use “Berserker Prime” [7]'):
            with self.subTest(invalid=invalid):
                result, llm = self.generate([AIMessage(content=FIXTURE['draft']), AIMessage(content=invalid)])
                self.assertEqual(llm.ainvoke.await_count, 2)
                self.assertEqual(result['generation_mode'], 'grounding_fallback')
                self.assertIn('Review evidence item(s) [1], [2], [3]', result['messages'][0].content)

    def test_repair_provider_error_keeps_fallback(self):
        result, llm = self.generate([AIMessage(content=FIXTURE['draft']), RuntimeError('offline')])
        self.assertEqual(llm.ainvoke.await_count, 2)
        self.assertEqual(result['generation_mode'], 'grounding_fallback')

    def test_valid_first_answer_never_retries(self):
        result, llm = self.generate([AIMessage(content=VALID)])
        self.assertEqual(llm.ainvoke.await_count, 1)
        self.assertEqual(result['generation_mode'], 'llm')

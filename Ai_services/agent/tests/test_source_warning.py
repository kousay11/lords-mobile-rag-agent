import asyncio
import copy
import unittest
from unittest.mock import AsyncMock, Mock, patch

from langchain_core.messages import AIMessage, HumanMessage
import graph


class SourceWarningTests(unittest.TestCase):
    def generate(self, outputs, statuses=('active', 'needs_review'), language='en'):
        chunks = [{'text': 'A new quest appears 15 minutes later.', 'score': 0.9,
                   'metadata': {'chunk_id': f'chunk-{i}', 'document_id': f'doc-{i}',
                                'title': 'Guide 2026', 'game_version': 'legacy-2026',
                                'status': status, 'reliability': 3}}
                  for i, status in enumerate(statuses)]
        original = copy.deepcopy(chunks)
        state = {'messages': [HumanMessage(content='How do Guild Fest quests work?')],
                 'language': language, 'player_context': {'response_length': 'short'},
                 'retrieved_documents': chunks}
        state.update(graph.validate_context_node(state))
        llm = Mock()
        llm.ainvoke = AsyncMock(side_effect=[AIMessage(content=x) if isinstance(x, str) else x for x in outputs])
        with patch('graph.get_llm', return_value=llm):
            result = asyncio.run(graph.generate_node(state, {'configurable': {}}))
        self.assertEqual(chunks, original)
        self.assertEqual(result['messages'][0].additional_kwargs['metadata']['sources'], state['sources'])
        return result['messages'][0].content, result['generation_mode']

    def test_uncited_needs_review_does_not_warn(self):
        text, mode = self.generate(['A new quest appears 15 minutes later. [1]'])
        self.assertEqual(text, 'A new quest appears 15 minutes later. [1]')
        self.assertEqual(mode, 'llm')

    def test_warning_names_only_cited_review_sources(self):
        text, _ = self.generate(['A new quest appears 15 minutes later. [1] [3] [3]'],
                                statuses=('active', 'needs_review', 'needs_review'))
        warning = text.split('\n\n')[0]
        self.assertIn('cited sources [3]', warning)
        self.assertNotIn('[1]', warning)
        self.assertNotIn('[2]', warning)
        self.assertEqual(warning.count('[3]'), 1)

    def test_year_and_version_warning_removed_in_all_languages(self):
        for language, prefix in [('en', 'Sources awaiting review'), ('fr', 'Sources avec réserves'), ('ar', 'مصادر قيد المراجعة')]:
            with self.subTest(language=language):
                text, _ = self.generate(['A new quest appears 15 minutes later. [2]'], language=language)
                warning = text.split('\n\n')[0]
                self.assertTrue(warning.startswith(prefix))
                self.assertIn('[2]', warning)
                for obsolete in ('year', 'version', 'année', 'سنتها', 'الإصدار', '2026'):
                    self.assertNotIn(obsolete, warning)

    def test_repaired_answer_drops_uncited_review_warning(self):
        text, mode = self.generate(['Use “unsupported item” [2]', 'A new quest appears 15 minutes later. [1]'])
        self.assertEqual(mode, 'llm_repaired')
        self.assertNotIn('Sources awaiting review', text)

    def test_repaired_answer_adds_warning_for_newly_cited_review_source(self):
        text, mode = self.generate(['Use “unsupported item” [1]', 'A new quest appears 15 minutes later. [2]'])
        self.assertEqual(mode, 'llm_repaired')
        self.assertIn('cited sources [2]', text)

    def test_fallback_uses_its_own_references_not_rejected_draft(self):
        for outputs, expected_mode in [(['Use “unsupported item” [2]'] * 2, 'grounding_fallback'),
                                       ([RuntimeError('offline')], 'safe_fallback')]:
            with self.subTest(mode=expected_mode):
                text, mode = self.generate(outputs)
                self.assertEqual(mode, expected_mode)
                self.assertIn('Review evidence item(s) [1]', text)
                self.assertNotIn('Sources awaiting review', text)

    def test_cited_active_and_deprecated_sources_do_not_warn(self):
        text, _ = self.generate(['A new quest appears 15 minutes later. [1] [2]'], statuses=('active', 'deprecated'))
        self.assertNotIn('Sources awaiting review', text)

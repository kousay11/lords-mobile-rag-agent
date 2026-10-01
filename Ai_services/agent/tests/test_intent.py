import unittest

from intent import (
    classify_intent,
    detect_language,
    extract_topics,
    needs_clarification,
    rewrite_queries,
)


class IntentTests(unittest.TestCase):
    def test_multilingual_greetings(self):
        self.assertEqual(classify_intent("Bonjour"), "greeting")
        self.assertEqual(classify_intent("hello"), "greeting")
        self.assertEqual(classify_intent("مرحبا"), "greeting")

    def test_lords_mobile_intents(self):
        self.assertEqual(
            classify_intent("Quel est le meilleur héros pour la chasse ?"),
            "recommendation",
        )
        self.assertEqual(
            classify_intent("Comment attaquer un Sombre nid ?"), "how_to"
        )
        self.assertEqual(
            classify_intent("Compare infanterie et cavalerie"), "comparison"
        )

    def test_automation_and_legacy_network_requests_are_out_of_scope(self):
        self.assertEqual(classify_intent("Automatiser mon compte avec un bot"), "out_of_scope")
        self.assertEqual(classify_intent("Analyse la packet loss du réseau"), "out_of_scope")

    def test_language_and_topic_extraction(self):
        self.assertEqual(detect_language("Which hero is best?"), "en")
        self.assertEqual(
            detect_language("Comment gagner cette bataille ?", requested="en"), "en"
        )
        self.assertEqual(detect_language("ما هو أفضل بطل؟"), "ar")
        self.assertIn("jewels", extract_topics("Quels joyaux pour la cavalerie ?"))
        self.assertIn("troops", extract_topics("Quels joyaux pour la cavalerie ?"))

    def test_recommendation_can_request_context(self):
        self.assertTrue(needs_clarification("Quel est le meilleur ?", "recommendation", {}))
        self.assertFalse(
            needs_clarification(
                "Quel est le meilleur héros pour la chasse ?", "recommendation", {}
            )
        )

    def test_universal_battle_claim_requires_clarification(self):
        self.assertTrue(
            needs_clarification(
                "Comment garantir que je gagne toutes les batailles ?", "how_to", {}
            )
        )

    def test_rewrite_adds_official_synonyms(self):
        rewritten = rewrite_queries("Comment attaquer un Sombre nid ?", ["darknests"])
        self.assertEqual(len(rewritten), 1)
        self.assertIn("Darknests", rewritten[0])

    def test_rewrite_appends_profile_terms(self):
        rewritten = rewrite_queries(
            "Quels héros choisir ?",
            ["heroes"],
            {"level": "Château 25", "play_style": "free_to_play", "response_length": "short"},
        )
        self.assertTrue(any("Château 25" in item for item in rewritten))
        self.assertTrue(any("free to play" in item for item in rewritten))


if __name__ == "__main__":
    unittest.main()

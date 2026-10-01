import unittest

from main import ChatRequest, ChatResponse, app


class ApiContractTests(unittest.TestCase):
    def test_chat_request_accepts_player_context(self):
        request = ChatRequest(
            message="Quels joyaux choisir ?",
            language="fr",
            player_context={"play_style": "free_to_play"},
        )
        self.assertEqual(request.language, "fr")
        self.assertEqual(request.player_context["play_style"], "free_to_play")

    def test_legacy_tuning_fields_are_ignored(self):
        request = ChatRequest(message="Bonjour", rrf_dense_weight=0.7, user_role="technical")
        self.assertEqual(request.message, "Bonjour")

    def test_response_is_explicitly_read_only(self):
        response = ChatResponse(
            thread_id="thread",
            response="Réponse",
            model="model",
            provider="provider",
            intent="fact_lookup",
            language="fr",
        )
        self.assertTrue(response.read_only)

    def test_only_lords_mobile_chat_routes_are_exposed(self):
        routes = {route.path for route in app.routes}
        self.assertIn("/chat", routes)
        self.assertIn("/threads/{thread_id}", routes)
        self.assertNotIn("/incident/analyze", routes)
        self.assertNotIn("/optimization/respond", routes)
        self.assertNotIn("/scenario", routes)

    def test_chat_unexpected_error_is_logged_and_stays_generic(self):
        from unittest.mock import AsyncMock, patch

        from fastapi.testclient import TestClient

        import main as main_module

        with (
            patch.object(
                main_module, "_invoke_chat", new=AsyncMock(side_effect=RuntimeError("boom"))
            ),
            patch.object(main_module.logger, "exception") as log_exc,
        ):
            response = TestClient(main_module.app).post("/chat", json={"message": "hi"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "boom")
        log_exc.assert_called_once()


if __name__ == "__main__":
    unittest.main()

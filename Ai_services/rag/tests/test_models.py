import sys
import unittest
from pathlib import Path

from pydantic import ValidationError


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from models import LordsMobileMetadata, RetrieveRequest  # noqa: E402


def valid_metadata() -> dict:
    return {
        "document_id": "official-buildings-001",
        "title": "Castle requirements",
        "source": "Official patch notes",
        "source_type": "official",
        "language": "en",
        "game_version": "5.0",
        "reliability": 5,
        "status": "active",
        "topics": ["buildings", "progression", "buildings"],
    }


class LordsMobileMetadataTests(unittest.TestCase):
    def test_normalizes_topics_and_sets_collection_date(self):
        metadata = LordsMobileMetadata.model_validate(valid_metadata())

        self.assertEqual(metadata.topics, ["buildings", "progression"])
        self.assertIsNotNone(metadata.collected_at)

    def test_rejects_invalid_reliability(self):
        data = valid_metadata()
        data["reliability"] = 6

        with self.assertRaises(ValidationError):
            LordsMobileMetadata.model_validate(data)

    def test_rejects_unknown_document_status(self):
        data = valid_metadata()
        data["status"] = "published"

        with self.assertRaises(ValidationError):
            LordsMobileMetadata.model_validate(data)

    def test_rejects_invalid_source_url(self):
        data = valid_metadata()
        data["url"] = "not-a-url"

        with self.assertRaises(ValidationError):
            LordsMobileMetadata.model_validate(data)

    def test_rejects_collection_date_without_timezone(self):
        data = valid_metadata()
        data["collected_at"] = "2026-09-06T10:00:00"

        with self.assertRaises(ValidationError):
            LordsMobileMetadata.model_validate(data)


class RetrieveRequestTests(unittest.TestCase):
    def test_active_status_is_the_safe_default(self):
        request = RetrieveRequest(query="castle level requirements")

        self.assertEqual(request.statuses, ["active"])

    def test_accepts_lords_mobile_filters(self):
        request = RetrieveRequest(
            query="cavalry familiar",
            language="fr",
            game_version="5.0",
            topic="familiars",
            entity_type="familiar",
            source_type="official",
            min_reliability=4,
        )

        self.assertEqual(request.language, "fr")
        self.assertEqual(request.min_reliability, 4)

    def test_rejects_empty_status_filter(self):
        with self.assertRaises(ValidationError):
            RetrieveRequest(query="castle", statuses=[])


if __name__ == "__main__":
    unittest.main()

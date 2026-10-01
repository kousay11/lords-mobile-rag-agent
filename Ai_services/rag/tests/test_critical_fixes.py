"""Critical safety tests: collection protection, min_score, Unicode, delete scope."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

import vector_store as vs
from models import IngestTextRequest  # noqa: E402


def _collection_info(dense_size=1024, dense_distance=None, sparse_modifier=None):
    from qdrant_client.models import Distance, Modifier

    dense_distance = dense_distance or Distance.COSINE
    sparse_modifier = sparse_modifier or Modifier.IDF
    return SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(
                vectors={"dense": SimpleNamespace(size=dense_size, distance=dense_distance)},
                sparse_vectors={"sparse": SimpleNamespace(modifier=sparse_modifier)},
            )
        )
    )


def _mock_qdrant(existing_names, collection_info=None, read_error=False):
    client = MagicMock()
    client.get_collections.return_value = SimpleNamespace(
        collections=[SimpleNamespace(name=n) for n in existing_names]
    )
    if read_error:
        client.get_collection.side_effect = ConnectionError("qdrant unreachable")
    else:
        client.get_collection.return_value = collection_info
    return client


def _client_with_mock(mock_client):
    with patch.object(vs, "QdrantClient", return_value=mock_client):
        return vs.VectorStoreClient(embedder=None)


def _backend_like_payload():
    return {
        "text": "Contenu documentaire suffisamment détaillé pour passer la validation.",
        "metadata": {
            "document_id": "11111111-1111-1111-1111-111111111111",
            "title": "Guide test",
            "source": "guide-test",
            "source_type": "official",
            "language": "fr",
            "reliability": 5,
            "status": "active",
            "collected_at": "2026-10-01T00:00:00+00:00",
            "topics": ["test"],
            "content_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        },
    }


class IngestContractTests(unittest.TestCase):
    def test_accepts_backend_payload_without_game_version(self):
        req = IngestTextRequest.model_validate(_backend_like_payload())
        self.assertEqual(req.metadata.document_id, "11111111-1111-1111-1111-111111111111")

    def test_rejects_game_version_as_forbidden_extra(self):
        from pydantic import ValidationError

        payload = _backend_like_payload()
        payload["metadata"] = dict(payload["metadata"], game_version="2026")
        with self.assertRaises(ValidationError):
            IngestTextRequest.model_validate(payload)


class CollectionProtectionTests(unittest.TestCase):
    def test_missing_collection_is_created(self):
        mock_client = _mock_qdrant([])
        _client_with_mock(mock_client)
        mock_client.create_collection.assert_called_once()
        mock_client.delete_collection.assert_not_called()

    def test_incompatible_schema_raises_without_deleting(self):
        mock_client = _mock_qdrant([vs.COLLECTION], _collection_info(dense_size=768))
        with self.assertRaises(RuntimeError):
            _client_with_mock(mock_client)
        mock_client.delete_collection.assert_not_called()

    def test_read_error_raises_without_deleting(self):
        mock_client = _mock_qdrant([vs.COLLECTION], read_error=True)
        with self.assertRaises(RuntimeError):
            _client_with_mock(mock_client)
        mock_client.delete_collection.assert_not_called()

    def test_compatible_collection_continues(self):
        mock_client = _mock_qdrant([vs.COLLECTION], _collection_info())
        _client_with_mock(mock_client)
        mock_client.delete_collection.assert_not_called()


class SemanticScoreTests(unittest.TestCase):
    def test_normalize_semantic_maps_cosine_range(self):
        self.assertAlmostEqual(vs.normalize_score(-1.0, "semantic"), 0.0)
        self.assertAlmostEqual(vs.normalize_score(0.0, "semantic"), 0.5)
        self.assertAlmostEqual(vs.normalize_score(1.0, "semantic"), 1.0)

    def test_search_respects_min_score(self):
        mock_client = _mock_qdrant([])
        store = _client_with_mock(mock_client)
        high = SimpleNamespace(score=0.9, payload={"text": "pertinent " * 20})
        low = SimpleNamespace(score=-0.9, payload={"text": "faible " * 20})
        mock_client.query_points.return_value = SimpleNamespace(points=[high, low])
        results = store.search([0.1] * 1024, top_k=5, min_score=0.5)
        self.assertEqual(len(results), 1)
        self.assertIn("pertinent", results[0]["text"])
        self.assertGreaterEqual(results[0]["score"], 0.5)


class UnicodeTokenizationTests(unittest.TestCase):
    def setUp(self):
        self.store = vs.VectorStoreClient.__new__(vs.VectorStoreClient)

    def test_arabic_tokens_survive(self):
        tokens = self.store._tokenize("دليل الحصون وترقية المباني في المملكة")
        self.assertTrue(len(tokens) >= 3, f"tokens={tokens}")

    def test_arabic_sparse_vector_is_not_empty(self):
        sparse = self.store._generate_sparse_vector("دليل الحصون وترقية المباني")
        self.assertTrue(len(sparse.indices) > 0)

    def test_french_tokens_still_work(self):
        tokens = self.store._tokenize("Guide des héros et monstres")
        self.assertIn("héros", tokens)


class DeleteScopeTests(unittest.TestCase):
    def test_delete_filters_on_document_id_only(self):
        from qdrant_client.models import CountResult

        mock_client = _mock_qdrant([])
        store = _client_with_mock(mock_client)
        mock_client.count.return_value = CountResult(count=2)
        deleted = store.delete_document("11111111-1111-1111-1111-111111111111")
        self.assertEqual(deleted, 2)
        _, kwargs = mock_client.delete.call_args
        selector = kwargs["points_selector"]
        dumped = selector.model_dump_json()
        self.assertIn("document_id", dumped)
        self.assertIn("11111111-1111-1111-1111-111111111111", dumped)
        self.assertNotIn('"source"', dumped)


if __name__ == "__main__":
    unittest.main()

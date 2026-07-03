import pytest
import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/categorization/categorize
# ─────────────────────────────────────────────────────────────────────────────

class TestCategorization:

    ENDPOINT = "/api/v1/categorization/categorize"

    def _mock_service(self, extract_return=None, extract_side_effect=None):
        """Patch CategorizationService so no DB or LLM is needed."""
        mock_service = MagicMock()
        if extract_side_effect:
            mock_service.extract.side_effect = extract_side_effect
        else:
            mock_service.extract.return_value = extract_return
        return mock_service

    # ── Happy path ────────────────────────────────────────────────────────────

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_valid_arabic_text_returns_items(self, mock_cls, client):
        """Arabic receipt text should return categorized items and total."""
        mock_cls.return_value = self._mock_service({
            "items": [
                {"id": 1, "item_name": "كفتة بالطماطم", "price": 75.0,
                 "category_name": "Food", "category_id": "ee44e469-9b14-4391-99f0-abc"}
            ],
            "grand_total": 75.0
        })
        payload = {"text": "كفتة بالطماطم ٧٥ جنيه", "user_id": str(uuid.uuid4())}
        resp = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["grand_total"] == 75.0
        assert data["items"][0]["item_name"] == "كفتة بالطماطم"
        assert data["items"][0]["category_name"] == "Food"

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_valid_english_text_returns_items(self, mock_cls, client):
        """English receipt text should return categorized items."""
        mock_cls.return_value = self._mock_service({
            "items": [
                {"id": 1, "item_name": "Pizza Margherita", "price": 120.0,
                 "category_name": "Food", "category_id": "ee44e469-9b14-4391-99f0-abc"},
                {"id": 2, "item_name": "Pepsi", "price": 25.0,
                 "category_name": "Drinks", "category_id": "9fb482dd-d27d-4c3c-b1a-xyz"}
            ],
            "grand_total": 145.0
        })
        payload = {"text": "Pizza Margherita 120 EGP\nPepsi 25 EGP\nTotal: 145 EGP",
                   "user_id": str(uuid.uuid4())}
        resp = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["grand_total"] == 145.0

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_mixed_arabic_english_text(self, mock_cls, client):
        """Mixed Arabic/English receipt (code-switching) should be handled."""
        mock_cls.return_value = self._mock_service({
            "items": [
                {"id": 1, "item_name": "وجبة", "price": 100.0,
                 "category_name": "Food", "category_id": "ee44e469-abc"},
                {"id": 2, "item_name": "Large Fries", "price": 45.0,
                 "category_name": "Food", "category_id": "ee44e469-abc"}
            ],
            "grand_total": 145.0
        })
        payload = {"text": "اشتريت وجبة ب 100 جنيه و Large Fries ب 45 جنيه",
                   "user_id": str(uuid.uuid4())}
        resp = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2
        assert resp.json()["items"][0]["item_name"] == "وجبة"
        assert resp.json()["grand_total"] == 145.0

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_empty_items_returned_when_no_items_found(self, mock_cls, client):
        """Unreadable receipt should return empty items list, not an error."""
        mock_cls.return_value = self._mock_service({
            "items": [],
            "grand_total": 0.0
        })
        payload = {"text": "<;`", "user_id": str(uuid.uuid4())}
        resp = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["grand_total"] == 0.0

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_null_category_id_accepted(self, mock_cls, client):
        """Items with unrecognized categories should have null category_id."""
        mock_cls.return_value = self._mock_service({
            "items": [
                {"id": 1, "item_name": "Mystery Item", "price": 50.0,
                 "category_name": None, "category_id": None}
            ],
            "grand_total": 50.0
        })
        payload = {"text": "Mystery Item 50", "user_id": str(uuid.uuid4())}
        resp = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        assert resp.json()["items"][0]["category_id"] is None

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_grand_total_matches_sum_of_items(self, mock_cls, client):
        """grand_total should equal the sum of item prices."""
        mock_cls.return_value = self._mock_service({
            "items": [
                {"id": 1, "item_name": "Item A", "price": 30.0,
                 "category_name": "Food", "category_id": "abc"},
                {"id": 2, "item_name": "Item B", "price": 70.0,
                 "category_name": "Food", "category_id": "abc"}
            ],
            "grand_total": 100.0
        })
        payload = {"text": "Item A 30\nItem B 70", "user_id": str(uuid.uuid4())}
        resp = client.post(self.ENDPOINT, json=payload)
        data  = resp.json()
        total = sum(item["price"] for item in data["items"])
        assert total == pytest.approx(data["grand_total"])

    # ── Validation errors ─────────────────────────────────────────────────────

    def test_missing_text_field_returns_422(self, client):
        """Request without 'text' field should return 422 Unprocessable Entity."""
        payload = {"user_id": str(uuid.uuid4())}
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 422

    def test_missing_user_id_returns_422(self, client):
        """Request without 'user_id' should return 422."""
        payload = {"text": "some receipt text"}
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 422

    def test_invalid_user_id_format_returns_422(self, client):
        """Non-UUID user_id should return 422."""
        payload = {"text": "some text", "user_id": "not-a-uuid"}
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 422

    def test_empty_body_returns_422(self, client):
        """Empty request body should return 422."""
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 422

    # ── LLM failure handling ──────────────────────────────────────────────────

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_llm_invalid_json_returns_422(self, mock_cls, client):
        """LLM returning non-JSON should surface as 422."""
        mock_cls.return_value = self._mock_service(
            extract_side_effect=HTTPException(status_code=422, detail="Model returned invalid JSON")
        )
        payload = {"text": "unreadable garbage text", "user_id": str(uuid.uuid4())}
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 422
        assert "invalid JSON" in resp.json()["detail"]

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_service_called_with_correct_user_id(self, mock_cls, client):
        """Service extract() must be called with the user_id from the request."""
        mock_service = self._mock_service({"items": [], "grand_total": 0.0})
        mock_cls.return_value = mock_service
        user_id = str(uuid.uuid4())
        payload = {"text": "receipt text", "user_id": user_id}
        client.post(self.ENDPOINT, json=payload)
        mock_service.extract.assert_called_once()
        call_kwargs = mock_service.extract.call_args
        assert str(user_id) in str(call_kwargs)

    # ── Response shape ────────────────────────────────────────────────────────

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_response_contains_items_and_grand_total(self, mock_cls, client):
        """Response must always have 'items' list and 'grand_total' field."""
        mock_cls.return_value = self._mock_service({"items": [], "grand_total": 0.0})
        payload = {"text": "text", "user_id": str(uuid.uuid4())}
        resp    = client.post(self.ENDPOINT, json=payload)
        data    = resp.json()
        assert "items"       in data
        assert "grand_total" in data
        assert isinstance(data["items"], list)

    @patch("spendoo.categorization.routes.CategorizationService")
    def test_each_item_has_required_fields(self, mock_cls, client):
        """Each item in response must have id, item_name, price, category fields."""
        mock_cls.return_value = self._mock_service({
            "items": [
                {"id": 1, "item_name": "Coffee", "price": 35.0,
                 "category_name": "Drinks", "category_id": "abc-123"}
            ],
            "grand_total": 35.0
        })
        payload = {"text": "Coffee 35 EGP", "user_id": str(uuid.uuid4())}
        resp    = client.post(self.ENDPOINT, json=payload)
        item    = resp.json()["items"][0]
        assert "id"            in item
        assert "item_name"     in item
        assert "price"         in item
        assert "category_name" in item
        assert "category_id"   in item
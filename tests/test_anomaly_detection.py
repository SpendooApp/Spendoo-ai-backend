import pytest
import uuid
from unittest.mock import MagicMock, patch
from decimal import Decimal
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/anomaly/detect
# ─────────────────────────────────────────────────────────────────────────────

class TestAnomalyDetect:

    ENDPOINT = "/api/v1/anomaly/detect"

    def _mock_response(self, **kwargs):
        from spendoo.anomaly_detection.models import AnomalyResponse
        defaults = dict(
            dates=["2026-06-01", "2026-06-02", "2026-06-03"],
            original_values=[100.0, 5000.0, 110.0],
            cleaned_values=[100.0, 105.0, 110.0],
            is_anomaly=[False, True, False],
            anomaly_dates=["2026-06-02"],
            anomaly_count=1,
            lower_bound=0.0,
            upper_bound=500.0
        )
        defaults.update(kwargs)
        return AnomalyResponse(**defaults)

    # ── Happy path ────────────────────────────────────────────────────────────

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_spike_detected_and_cleaned(self, mock_cls, client):
        """A clear spending spike should be flagged and cleaned."""
        mock_cls.return_value.detect.return_value = self._mock_response()
        payload = {"user_id": str(uuid.uuid4()), "days": 30}
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["anomaly_count"] == 1
        assert data["anomaly_dates"] == ["2026-06-02"]
        assert data["is_anomaly"][1] is True
        assert data["cleaned_values"][1] < 5000.0

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_no_anomalies_in_normal_spending(self, mock_cls, client):
        """Normal consistent spending should return zero anomalies."""
        mock_cls.return_value.detect.return_value = self._mock_response(
            dates=["2026-06-01", "2026-06-02", "2026-06-03"],
            original_values=[100.0, 110.0, 105.0],
            cleaned_values=[100.0, 110.0, 105.0],
            is_anomaly=[False, False, False],
            anomaly_dates=[],
            anomaly_count=0,
            lower_bound=0.0,
            upper_bound=300.0
        )
        payload = {"user_id": str(uuid.uuid4()), "days": 30}
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        assert resp.json()["anomaly_count"] == 0
        assert resp.json()["anomaly_dates"] == []

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_empty_history_returns_zero_anomalies(self, mock_cls, client):
        """User with no transactions should return empty response gracefully."""
        mock_cls.return_value.detect.return_value = self._mock_response(
            dates=[], original_values=[], cleaned_values=[],
            is_anomaly=[], anomaly_dates=[], anomaly_count=0,
            lower_bound=0.0, upper_bound=0.0
        )
        payload = {"user_id": str(uuid.uuid4()), "days": 30}
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        assert resp.json()["anomaly_count"] == 0

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_multiple_anomalies_all_flagged(self, mock_cls, client):
        """Multiple spikes should all appear in anomaly_dates."""
        mock_cls.return_value.detect.return_value = self._mock_response(
            dates=["2026-06-01", "2026-06-02", "2026-06-03",
                   "2026-06-04", "2026-06-05"],
            original_values=[100.0, 5000.0, 110.0, 4800.0, 105.0],
            cleaned_values=[100.0, 103.0, 110.0, 107.0, 105.0],
            is_anomaly=[False, True, False, True, False],
            anomaly_dates=["2026-06-02", "2026-06-04"],
            anomaly_count=2,
            lower_bound=0.0,
            upper_bound=500.0
        )
        payload = {"user_id": str(uuid.uuid4()), "days": 30}
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["anomaly_count"] == 2
        assert "2026-06-02" in data["anomaly_dates"]
        assert "2026-06-04" in data["anomaly_dates"]

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_cleaned_values_never_exceed_original_spike(self, mock_cls, client):
        """Cleaned values must be lower than detected anomaly values."""
        mock_cls.return_value.detect.return_value = self._mock_response(
            original_values=[100.0, 9999.0, 110.0],
            cleaned_values=[100.0, 105.0, 110.0],
        )
        payload = {"user_id": str(uuid.uuid4()), "days": 30}
        resp    = client.post(self.ENDPOINT, json=payload)
        data    = resp.json()
        assert data["cleaned_values"][1] < 9999.0

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_lower_bound_is_never_negative(self, mock_cls, client):
        """lower_bound in response should always be >= 0."""
        mock_cls.return_value.detect.return_value = self._mock_response(
            lower_bound=0.0
        )
        payload = {"user_id": str(uuid.uuid4()), "days": 30}
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.json()["lower_bound"] >= 0.0

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_default_days_used_when_not_provided(self, mock_cls, client):
        """When days not specified, default (30) should be used."""
        mock_service = MagicMock()
        mock_service.detect.return_value = self._mock_response(
            dates=[], original_values=[], cleaned_values=[],
            is_anomaly=[], anomaly_dates=[], anomaly_count=0,
            lower_bound=0.0, upper_bound=0.0
        )
        mock_cls.return_value = mock_service
        payload = {"user_id": str(uuid.uuid4())}   # no days field
        resp    = client.post(self.ENDPOINT, json=payload)
        assert resp.status_code == 200
        mock_service.detect.assert_called_once()
        call_kwargs = mock_service.detect.call_args
        assert call_kwargs[1].get("days", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else 30) == 30

    # ── Response shape ────────────────────────────────────────────────────────

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_response_has_all_required_fields(self, mock_cls, client):
        """Response must contain all expected fields."""
        mock_cls.return_value.detect.return_value = self._mock_response()
        payload = {"user_id": str(uuid.uuid4()), "days": 20}
        resp    = client.post(self.ENDPOINT, json=payload)
        data    = resp.json()
        required_fields = [
            "dates", "original_values", "cleaned_values",
            "is_anomaly", "anomaly_dates", "anomaly_count",
            "lower_bound", "upper_bound"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_dates_original_cleaned_same_length(self, mock_cls, client):
        """dates, original_values, cleaned_values, is_anomaly must all be same length."""
        mock_cls.return_value.detect.return_value = self._mock_response()
        payload = {"user_id": str(uuid.uuid4()), "days": 30}
        resp    = client.post(self.ENDPOINT, json=payload)
        data    = resp.json()
        assert len(data["dates"]) == len(data["original_values"])
        assert len(data["dates"]) == len(data["cleaned_values"])
        assert len(data["dates"]) == len(data["is_anomaly"])

    @patch("spendoo.anomaly_detection.routes.AnomalyService")
    def test_anomaly_dates_subset_of_all_dates(self, mock_cls, client):
        """Every date in anomaly_dates must exist in dates list."""
        mock_cls.return_value.detect.return_value = self._mock_response()
        payload = {"user_id": str(uuid.uuid4()), "days": 30}
        resp    = client.post(self.ENDPOINT, json=payload)
        data    = resp.json()
        for anomaly_date in data["anomaly_dates"]:
            assert anomaly_date in data["dates"]

    # ── Validation errors ─────────────────────────────────────────────────────

    def test_missing_user_id_returns_422(self, client):
        """Request without user_id should return 422."""
        resp = client.post(self.ENDPOINT, json={"days": 30})
        assert resp.status_code == 422

    def test_invalid_user_id_returns_422(self, client):
        """Non-UUID user_id should return 422."""
        resp = client.post(self.ENDPOINT, json={"user_id": "not-a-uuid", "days": 30})
        assert resp.status_code == 422

    def test_negative_days_returns_422(self, client):
        """Negative days value should be rejected."""
        resp = client.post(self.ENDPOINT, json={"user_id": str(uuid.uuid4()), "days": -5})
        assert resp.status_code == 422

    def test_zero_days_returns_422(self, client):
        """Zero days should be rejected — no window to analyse."""
        resp = client.post(self.ENDPOINT, json={"user_id": str(uuid.uuid4()), "days": 0})
        assert resp.status_code == 422

    def test_empty_body_returns_422(self, client):
        """Empty request body should return 422."""
        resp = client.post(self.ENDPOINT, json={})
        assert resp.status_code == 422
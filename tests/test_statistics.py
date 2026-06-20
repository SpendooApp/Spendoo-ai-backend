import pytest
from unittest.mock import MagicMock
from datetime import datetime
import uuid
from decimal import Decimal
from fastapi.testclient import TestClient

from app import create_app
from spendoo.statistics.service import StatisticsService
from spendoo.statistics.models import Granularity, FinancialStatsResponse, StatsBucketDto
from spendoo.core.models import BudgetORM, TransactionORM

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def service(mock_db):
    svc = StatisticsService(mock_db)
    svc.repo = MagicMock()
    return svc

def test_generate_buckets_daily(service):
    start = datetime(2026, 6, 19, 14, 30)
    end = datetime(2026, 6, 21, 10, 0)
    buckets = service._generate_buckets(start, end, Granularity.DAY)
    
    assert len(buckets) == 3
    assert buckets[0]["start"] == datetime(2026, 6, 19, 0, 0)
    assert buckets[0]["end"] == datetime(2026, 6, 20, 0, 0)
    assert buckets[1]["start"] == datetime(2026, 6, 20, 0, 0)
    assert buckets[1]["end"] == datetime(2026, 6, 21, 0, 0)

def test_generate_buckets_monthly(service):
    start = datetime(2026, 4, 15)
    end = datetime(2026, 6, 10)
    buckets = service._generate_buckets(start, end, Granularity.MONTH)
    
    assert len(buckets) == 3
    assert buckets[0]["start"] == datetime(2026, 4, 1, 0, 0)
    assert buckets[0]["end"] == datetime(2026, 5, 1, 0, 0)
    assert buckets[1]["start"] == datetime(2026, 5, 1, 0, 0)
    assert buckets[1]["end"] == datetime(2026, 6, 1, 0, 0)
    assert buckets[2]["start"] == datetime(2026, 6, 1, 0, 0)
    assert buckets[2]["end"] == datetime(2026, 7, 1, 0, 0)

def test_calculate_intersecting_days(service):
    # Perfect overlap
    days = service._calculate_intersecting_days(
        datetime(2026, 6, 1), datetime(2026, 6, 30),
        datetime(2026, 6, 1), datetime(2026, 6, 30)
    )
    assert days == 29 # days difference: 30 - 1 = 29

    # Partial overlap
    days = service._calculate_intersecting_days(
        datetime(2026, 6, 15), datetime(2026, 6, 25),
        datetime(2026, 6, 20), datetime(2026, 7, 1)
    )
    assert days == 5 # 20 to 25

def test_budget_downscaling_yearly_to_monthly(service):
    # Yearly budget of 1200 overlapping a full month (30 days)
    # Factor: 12. Divisor: 12. Overlap fraction: 30/30 = 1.0. Expected = 100.
    cat_id = uuid.uuid4()
    budget = BudgetORM(
        id=uuid.uuid4(),
        category_id=cat_id,
        amount=Decimal("1200.00"),
        period=365,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2027, 1, 1),
        is_active=True
    )
    
    val = service._calculate_category_budget_for_bucket(
        [budget],
        datetime(2026, 6, 1),
        datetime(2026, 7, 1),
        Granularity.MONTH
    )
    assert float(val) == 100.0

def test_budget_same_level_overlap(service):
    # Monthly budget overlapping monthly granularity.
    # Should select the latest active one (by start_date) and NOT sum them.
    cat_id = uuid.uuid4()
    b1 = BudgetORM(
        id=uuid.uuid4(),
        category_id=cat_id,
        amount=Decimal("500.00"),
        period=30,
        start_date=datetime(2026, 6, 1),
        end_date=datetime(2026, 7, 1),
        is_active=True
    )
    b2 = BudgetORM(
        id=uuid.uuid4(),
        category_id=cat_id,
        amount=Decimal("600.00"),
        period=30,
        start_date=datetime(2026, 6, 10),
        end_date=datetime(2026, 7, 10),
        is_active=True
    )
    
    val = service._calculate_category_budget_for_bucket(
        [b1, b2],
        datetime(2026, 6, 1),
        datetime(2026, 7, 1),
        Granularity.MONTH
    )
    assert float(val) == 600.0

def test_budget_upscaling_daily_to_monthly(service):
    # Daily budgets of 10 overlapping a month.
    # E.g. one daily budget on 2026-06-15, period=1. Overlaps month of June by 1 day.
    # Contribution: 10 / 1 * 1 = 10.
    cat_id = uuid.uuid4()
    b = BudgetORM(
        id=uuid.uuid4(),
        category_id=cat_id,
        amount=Decimal("10.00"),
        period=1,
        start_date=datetime(2026, 6, 15),
        end_date=datetime(2026, 6, 16),
        is_active=True
    )
    
    val = service._calculate_category_budget_for_bucket(
        [b],
        datetime(2026, 6, 1),
        datetime(2026, 7, 1),
        Granularity.MONTH
    )
    assert float(val) == 10.0

def test_calculate_stats_integration(service):
    user_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    
    # Mock repository data
    service.repo.get_transactions_in_range.return_value = [
        TransactionORM(amount=Decimal("-50.00"), transaction_date=datetime(2026, 6, 19, 10, 0), user_id=user_id, category_id=cat_id),
        TransactionORM(amount=Decimal("150.00"), transaction_date=datetime(2026, 6, 20, 14, 0), user_id=user_id, category_id=cat_id)
    ]
    service.repo.get_overlapping_budgets.return_value = [
        BudgetORM(category_id=cat_id, amount=Decimal("30.00"), period=1, start_date=datetime(2026, 6, 19), end_date=datetime(2026, 6, 20), is_active=True)
    ]

    res = service.calculate_stats(
        user_id=user_id,
        granularity=Granularity.DAY,
        start_date=datetime(2026, 6, 19),
        end_date=datetime(2026, 6, 21)
    )

    assert len(res.buckets) == 2
    # Bucket 1: 2026-06-19 to 2026-06-20
    assert res.buckets[0].spending == Decimal("50.00")
    assert res.buckets[0].income == Decimal("0.00")
    assert res.buckets[0].budget == Decimal("30.00")
    
    # Bucket 2: 2026-06-20 to 2026-06-21
    assert res.buckets[1].spending == Decimal("0.00")
    assert res.buckets[1].income == Decimal("150.00")
    assert res.buckets[1].budget == Decimal("0.00")

    assert res.highest_spending_bucket_index == 0

def test_calculate_api_endpoint(mock_db):
    # Test client calling the FastAPI route
    app = create_app({'TESTING': True})
    client = TestClient(app)
    
    # We mock calculate_stats method on StatisticsService
    mock_response = FinancialStatsResponse(
        buckets=[
            StatsBucketDto(spending=Decimal("50.00"), income=Decimal("0.00"), budget=Decimal("30.00"), start_date=datetime(2026, 6, 19))
        ],
        highest_spending_bucket_index=0
    )
    
    # We patch StatisticsService.calculate_stats
    original_calc = StatisticsService.calculate_stats
    StatisticsService.calculate_stats = MagicMock(return_value=mock_response)
    
    try:
        payload = {
            "user_id": str(uuid.uuid4()),
            "granularity": "DAY",
            "start_date": "2026-06-19T00:00:00",
            "end_date": "2026-06-20T00:00:00"
        }
        resp = client.post("/api/v1/statistics/calculate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["highest_spending_bucket_index"] == 0
        assert data["buckets"][0]["spending"] == "50.00"
    finally:
        # Restore original method
        StatisticsService.calculate_stats = original_calc

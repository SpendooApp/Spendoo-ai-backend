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
        highest_spending_bucket_index=0,
        highest_value=Decimal("50.00")
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
        assert data["highest_value"] == "50.00"
    finally:
        # Restore original method
        StatisticsService.calculate_stats = original_calc


def test_generate_buckets_weekly_sunday_to_saturday(service):
    # Sunday is June 14, Monday is June 15, Saturday is June 20
    start = datetime(2026, 6, 15, 14, 30) # Monday
    end = datetime(2026, 6, 21, 10, 0) # Next Sunday (June 21 is a Sunday)
    buckets = service._generate_buckets(start, end, Granularity.WEEK)
    
    assert len(buckets) == 2
    # Week 1: June 14 (Sunday) to June 21 (Sunday)
    assert buckets[0]["start"] == datetime(2026, 6, 14, 0, 0)
    assert buckets[0]["end"] == datetime(2026, 6, 21, 0, 0)
    # Week 2: June 21 (Sunday) to June 28 (Sunday)
    assert buckets[1]["start"] == datetime(2026, 6, 21, 0, 0)
    assert buckets[1]["end"] == datetime(2026, 6, 28, 0, 0)

def test_calculate_stats_highest_value_integration(service):
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

    # Bucket 0: spending=50.00, income=0.00, budget=30.00 -> max(50.00, 30.00) = 50.00
    # Bucket 1: spending=0.00, income=150.00, budget=0.00 -> max(0.00, 150.00) = 150.00
    # highest_value = 150.00
    assert res.highest_value == Decimal("150.00")

def test_calculate_budget_status_service(service):
    user_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    
    # 3 buckets:
    # Bucket 0: spending=30.00, limit=100.00 (30% -> within)
    # Bucket 1: spending=95.00, limit=100.00 (95% -> risk)
    # Bucket 2: spending=110.00, limit=100.00 (110% -> overspend)
    service.repo.get_transactions_in_range.return_value = [
        TransactionORM(amount=Decimal("-30.00"), transaction_date=datetime(2026, 6, 19, 10, 0), user_id=user_id, category_id=cat_id),
        TransactionORM(amount=Decimal("-95.00"), transaction_date=datetime(2026, 6, 20, 10, 0), user_id=user_id, category_id=cat_id),
        TransactionORM(amount=Decimal("-110.00"), transaction_date=datetime(2026, 6, 21, 10, 0), user_id=user_id, category_id=cat_id)
    ]
    service.repo.get_overlapping_budgets.return_value = [
        BudgetORM(category_id=cat_id, amount=Decimal("100.00"), period=1, start_date=datetime(2026, 6, 19), end_date=datetime(2026, 6, 22), is_active=True)
    ]

    res = service.calculate_budget_status(
        user_id=user_id,
        granularity=Granularity.DAY,
        start_date=datetime(2026, 6, 19),
        end_date=datetime(2026, 6, 22)
    )

    assert len(res.buckets) == 3
    assert res.buckets[0].status == "within"
    assert res.buckets[0].percentage == Decimal("30.00")
    
    assert res.buckets[1].status == "risk"
    assert res.buckets[1].percentage == Decimal("95.00")
    
    assert res.buckets[2].status == "overspend"
    assert res.buckets[2].percentage == Decimal("110.00")

    assert res.highest_spending == Decimal("110.00")

def test_get_top_categories_service(service):
    from spendoo.categorization.models import CategoryORM
    user_id = uuid.uuid4()
    cat1_id = uuid.uuid4()
    cat2_id = uuid.uuid4()
    
    # Mock categories
    service.repo.get_user_categories.return_value = [
        CategoryORM(id=cat1_id, category_name="Food", category_icon="fastfood", user_id=user_id),
        CategoryORM(id=cat2_id, category_name="Rent", category_icon="home", user_id=user_id)
    ]

    # Current bucket is June 2026
    # Previous bucket is May 2026
    # Food: June spending = 300, May spending = 200 (change = +50%)
    # Rent: June spending = 1000, May spending = 0 (change = +100%)
    service.repo.get_transactions_in_range.side_effect = lambda uid, start, end: (
        [
            # June transactions
            TransactionORM(amount=Decimal("-300.00"), transaction_date=datetime(2026, 6, 10), user_id=user_id, category_id=cat1_id),
            TransactionORM(amount=Decimal("-1000.00"), transaction_date=datetime(2026, 6, 15), user_id=user_id, category_id=cat2_id)
        ]
        if start.month == 6 else
        [
            # May transactions
            TransactionORM(amount=Decimal("-200.00"), transaction_date=datetime(2026, 5, 10), user_id=user_id, category_id=cat1_id)
        ]
    )

    # Call with now = 2026-07-20
    res = service.get_top_categories(
        user_id=user_id,
        granularity=Granularity.MONTH,
        now=datetime(2026, 7, 20)
    )

    assert res.total_spending == Decimal("1300.00")
    assert len(res.top_categories) == 2
    
    # Sorted from highest to lowest: Rent (1000) then Food (300)
    assert res.top_categories[0].category_name == "Rent"
    assert res.top_categories[0].spending == Decimal("1000.00")
    assert res.top_categories[0].percentage_change == Decimal("100.00")
    assert res.top_categories[0].contribution_percentage == Decimal("76.92")
    
    assert res.top_categories[1].category_name == "Food"
    assert res.top_categories[1].spending == Decimal("300.00")
    assert res.top_categories[1].percentage_change == Decimal("50.00")
    assert res.top_categories[1].contribution_percentage == Decimal("23.08")

def test_new_endpoints_api_calls(mock_db):
    app = create_app({'TESTING': True})
    client = TestClient(app)
    
    # Mock budget status
    from spendoo.statistics.models import BudgetStatusBucketDto, BudgetStatusResponse, BudgetStatus
    mock_status_response = BudgetStatusResponse(
        buckets=[
            BudgetStatusBucketDto(spending=Decimal("50.00"), status=BudgetStatus.WITHIN, percentage=Decimal("50.00"), start_date=datetime(2026, 6, 19))
        ],
        highest_spending=Decimal("50.00")
    )
    
    # Mock top categories
    from spendoo.statistics.models import CategorySpendingDto, TopCategoriesResponse
    mock_top_response = TopCategoriesResponse(
        total_spending=Decimal("50.00"),
        top_categories=[
            CategorySpendingDto(category_id=uuid.uuid4(), category_name="Food", category_icon="fastfood", spending=Decimal("50.00"), percentage_change=Decimal("20.00"), contribution_percentage=Decimal("100.00"))
        ]
    )
    
    original_status = StatisticsService.calculate_budget_status
    original_categories = StatisticsService.get_top_categories
    
    StatisticsService.calculate_budget_status = MagicMock(return_value=mock_status_response)
    StatisticsService.get_top_categories = MagicMock(return_value=mock_top_response)
    
    try:
        user_uuid = str(uuid.uuid4())
        
        # 1. Budget status endpoint
        payload = {
            "user_id": user_uuid,
            "granularity": "DAY",
            "start_date": "2026-06-19T00:00:00",
            "end_date": "2026-06-20T00:00:00"
        }
        resp = client.post("/api/v1/statistics/budget-status", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["highest_spending"] == "50.00"
        assert data["buckets"][0]["status"] == "within"
        
        # 2. Top categories endpoint
        resp = client.get(f"/api/v1/statistics/top-categories?user_id={user_uuid}&granularity=DAY")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_spending"] == "50.00"
        assert data["top_categories"][0]["category_name"] == "Food"
        assert data["top_categories"][0]["contribution_percentage"] == "100.00"
        
    finally:
        StatisticsService.calculate_budget_status = original_status
        StatisticsService.get_top_categories = original_categories


def test_calculate_combined_stats_service_correctness(service):
    from spendoo.categorization.models import CategoryORM
    user_id = uuid.uuid4()
    cat_id = uuid.uuid4()

    # Mock categories
    service.repo.get_user_categories.return_value = [
        CategoryORM(id=cat_id, category_name="Food", category_icon="fastfood", user_id=user_id)
    ]

    # Preceding date range will be 2026-06-18
    # Start: 2026-06-19, End: 2026-06-21 (2 buckets: 19th and 20th)
    service.repo.get_transactions_in_range.return_value = [
        # Preceding bucket transaction (June 18)
        TransactionORM(amount=Decimal("-100.00"), transaction_date=datetime(2026, 6, 18, 12, 0), user_id=user_id, category_id=cat_id),
        # Bucket 1 transaction (June 19)
        TransactionORM(amount=Decimal("-50.00"), transaction_date=datetime(2026, 6, 19, 10, 0), user_id=user_id, category_id=cat_id),
        # Bucket 2 transaction (June 20)
        TransactionORM(amount=Decimal("-150.00"), transaction_date=datetime(2026, 6, 20, 14, 0), user_id=user_id, category_id=cat_id)
    ]
    service.repo.get_overlapping_budgets.return_value = [
        BudgetORM(category_id=cat_id, amount=Decimal("120.00"), period=1, start_date=datetime(2026, 6, 19), end_date=datetime(2026, 6, 21), is_active=True)
    ]

    res = service.calculate_combined_stats(
        user_id=user_id,
        granularity=Granularity.DAY,
        start_date=datetime(2026, 6, 19),
        end_date=datetime(2026, 6, 21),
        now=datetime(2026, 6, 21)
    )

    # 1. Financial stats checks
    assert len(res.financial_stats.buckets) == 2
    assert res.financial_stats.buckets[0].spending == Decimal("50.00")
    assert res.financial_stats.buckets[1].spending == Decimal("150.00")
    assert res.financial_stats.highest_value == Decimal("150.00") # max(150.00, 120.00)
    assert res.financial_stats.highest_spending_bucket_index == 1

    # 2. Budget status checks
    assert len(res.budget_status.buckets) == 2
    assert res.budget_status.buckets[0].spending == Decimal("50.00")
    assert res.budget_status.buckets[0].status == "within" # 50 / 120 = 41.6%
    assert res.budget_status.buckets[1].spending == Decimal("150.00")
    assert res.budget_status.buckets[1].status == "overspend" # 150 / 120 = 125%
    assert res.budget_status.highest_spending == Decimal("150.00")

    # 3. Top categories checks
    assert res.top_categories.total_spending == Decimal("150.00") # Spending in last bucket (Bucket 2)
    assert len(res.top_categories.top_categories) == 1
    assert res.top_categories.top_categories[0].category_name == "Food"
    assert res.top_categories.top_categories[0].spending == Decimal("150.00")
    # Previous spending (June 19) = 50.00. Current (June 20) = 150.00.
    # Percentage change = ((150 - 50) / 50) * 100 = +200%
    assert res.top_categories.top_categories[0].percentage_change == Decimal("200.00")
    assert res.top_categories.top_categories[0].contribution_percentage == Decimal("100.00")


def test_combined_api_endpoint(mock_db):
    app = create_app({'TESTING': True})
    client = TestClient(app)

    from spendoo.statistics.models import (
        CombinedStatsResponse,
        StatsBucketDto,
        BudgetStatusBucketDto,
        BudgetStatus,
        CategorySpendingDto,
        BudgetStatusResponse,
        TopCategoriesResponse
    )
    mock_combined_response = CombinedStatsResponse(
        financial_stats=FinancialStatsResponse(
            buckets=[StatsBucketDto(spending=Decimal("50.00"), income=Decimal("0.00"), budget=Decimal("30.00"), start_date=datetime(2026, 6, 19))],
            highest_spending_bucket_index=0,
            highest_value=Decimal("50.00")
        ),
        budget_status=BudgetStatusResponse(
            buckets=[BudgetStatusBucketDto(spending=Decimal("50.00"), status=BudgetStatus.WITHIN, percentage=Decimal("50.00"), start_date=datetime(2026, 6, 19))],
            highest_spending=Decimal("50.00")
        ),
        top_categories=TopCategoriesResponse(
            total_spending=Decimal("50.00"),
            top_categories=[CategorySpendingDto(category_id=uuid.uuid4(), category_name="Food", category_icon="fastfood", spending=Decimal("50.00"), percentage_change=Decimal("20.00"), contribution_percentage=Decimal("100.00"))]
        )
    )

    original_combined = StatisticsService.calculate_combined_stats
    StatisticsService.calculate_combined_stats = MagicMock(return_value=mock_combined_response)

    try:
        payload = {
            "user_id": str(uuid.uuid4()),
            "granularity": "DAY",
            "start_date": "2026-06-19T00:00:00",
            "end_date": "2026-06-20T00:00:00"
        }
        resp = client.post("/api/v1/statistics/combined", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "financial_stats" in data
        assert "budget_status" in data
        assert "top_categories" in data
        assert data["financial_stats"]["highest_value"] == "50.00"
        assert data["budget_status"]["highest_spending"] == "50.00"
        assert data["top_categories"]["top_categories"][0]["category_name"] == "Food"
        assert data["top_categories"]["top_categories"][0]["contribution_percentage"] == "100.00"
    finally:
        StatisticsService.calculate_combined_stats = original_combined


def test_income_subtraction_for_category_less_negative_transactions(service):
    user_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    
    # Bucket: 2026-06-19 to 2026-06-20
    # Transactions:
    # 1. Income: +150.00
    # 2. Moving to budget (negative, no category): -50.00
    # Net income should be 150.00 - 50.00 = 100.00
    service.repo.get_transactions_in_range.return_value = [
        TransactionORM(amount=Decimal("150.00"), transaction_date=datetime(2026, 6, 19, 10, 0), user_id=user_id, category_id=cat_id),
        TransactionORM(amount=Decimal("-50.00"), transaction_date=datetime(2026, 6, 19, 12, 0), user_id=user_id, category_id=None)
    ]
    service.repo.get_overlapping_budgets.return_value = []

    res = service.calculate_stats(
        user_id=user_id,
        granularity=Granularity.DAY,
        start_date=datetime(2026, 6, 19),
        end_date=datetime(2026, 6, 20)
    )

    assert len(res.buckets) == 1
    assert res.buckets[0].income == Decimal("100.00")
    assert res.buckets[0].spending == Decimal("0.00")


def test_budget_status_ignores_income(service):
    user_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    
    # Bucket 0: spending = 95.00, budget = 100.00, income = 50.00
    # If compared with budget + income = 150.00, then 95 / 150 = 63.3% -> within
    # If compared only with budget = 100.00, then 95 / 100 = 95% -> risk
    service.repo.get_transactions_in_range.return_value = [
        # Income transaction (+50.00)
        TransactionORM(amount=Decimal("50.00"), transaction_date=datetime(2026, 6, 19, 9, 0), user_id=user_id, category_id=cat_id),
        # Spending transaction (-95.00)
        TransactionORM(amount=Decimal("-95.00"), transaction_date=datetime(2026, 6, 19, 10, 0), user_id=user_id, category_id=cat_id)
    ]
    service.repo.get_overlapping_budgets.return_value = [
        BudgetORM(category_id=cat_id, amount=Decimal("100.00"), period=1, start_date=datetime(2026, 6, 19), end_date=datetime(2026, 6, 20), is_active=True)
    ]

    res = service.calculate_budget_status(
        user_id=user_id,
        granularity=Granularity.DAY,
        start_date=datetime(2026, 6, 19),
        end_date=datetime(2026, 6, 20)
    )

    assert len(res.buckets) == 1
    assert res.buckets[0].status == "risk"
    assert res.buckets[0].percentage == Decimal("95.00")


def test_calculate_combined_stats_empty_transactions(service):
    user_id = uuid.uuid4()
    service.repo.get_user_categories.return_value = []
    service.repo.get_transactions_in_range.return_value = []
    service.repo.get_overlapping_budgets.return_value = []

    res = service.calculate_combined_stats(
        user_id=user_id,
        granularity=Granularity.DAY,
        start_date=datetime(2026, 6, 19),
        end_date=datetime(2026, 6, 21),
        now=datetime(2026, 6, 21)
    )

    assert res.top_categories.total_spending == Decimal("0.00")
    assert len(res.top_categories.top_categories) == 0


def test_calculate_budget_status_now_limitation(service):
    user_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    
    service.repo.get_transactions_in_range.return_value = [
        TransactionORM(amount=Decimal("-30.00"), transaction_date=datetime(2026, 6, 19, 10, 0), user_id=user_id, category_id=cat_id),
    ]
    service.repo.get_overlapping_budgets.return_value = [
        BudgetORM(category_id=cat_id, amount=Decimal("100.00"), period=1, start_date=datetime(2026, 6, 19), end_date=datetime(2026, 6, 22), is_active=True)
    ]

    res = service.calculate_budget_status(
        user_id=user_id,
        granularity=Granularity.DAY,
        start_date=datetime(2026, 6, 19),
        end_date=datetime(2026, 6, 22),
        now=datetime(2026, 6, 20)  # min(end_date, now) = June 20
    )

    assert len(res.buckets) == 1
    assert res.buckets[0].start_date == datetime(2026, 6, 19)
    assert res.buckets[0].spending == Decimal("30.00")


def test_calculate_combined_stats_now_limitation_budget_status(service):
    from spendoo.categorization.models import CategoryORM
    user_id = uuid.uuid4()
    cat_id = uuid.uuid4()

    service.repo.get_user_categories.return_value = [
        CategoryORM(id=cat_id, category_name="Food", category_icon="fastfood", user_id=user_id)
    ]
    service.repo.get_transactions_in_range.return_value = [
        TransactionORM(amount=Decimal("-30.00"), transaction_date=datetime(2026, 6, 19, 10, 0), user_id=user_id, category_id=cat_id),
    ]
    service.repo.get_overlapping_budgets.return_value = [
        BudgetORM(category_id=cat_id, amount=Decimal("100.00"), period=1, start_date=datetime(2026, 6, 19), end_date=datetime(2026, 6, 22), is_active=True)
    ]

    res = service.calculate_combined_stats(
        user_id=user_id,
        granularity=Granularity.DAY,
        start_date=datetime(2026, 6, 19),
        end_date=datetime(2026, 6, 22),
        now=datetime(2026, 6, 20)  # min(end_date, now) = June 20
    )

    assert len(res.financial_stats.buckets) == 3
    assert len(res.budget_status.buckets) == 1
    assert res.budget_status.buckets[0].start_date == datetime(2026, 6, 19)







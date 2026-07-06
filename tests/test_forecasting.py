import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import uuid
from decimal import Decimal

from spendoo.forecasting.service import ForecastService
from spendoo.statistics.models import Granularity, StatsRequest
from spendoo.statistics.models import CombinedStatsResponse, FinancialStatsResponse, StatsBucketDto, BudgetStatusResponse, TopCategoriesResponse, BudgetStatusBucketDto, BudgetStatus
from spendoo.forecasting.models import CombinedForecastResponse

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def service(mock_db):
    svc = ForecastService(mock_db)
    svc.stats_service = MagicMock()
    svc.anomaly = MagicMock()
    return svc

def test_forecast_buckets_combined_with_offset_naive_dates(service):
    user_id = uuid.uuid4()
    
    # Mock return value of calculate_combined_stats
    mock_stats_response = CombinedStatsResponse(
        financial_stats=FinancialStatsResponse(
            buckets=[
                StatsBucketDto(spending=Decimal("50.00"), income=Decimal("0.00"), budget=Decimal("30.00"), start_date=datetime(2026, 6, 19, tzinfo=timezone.utc))
            ],
            highest_spending_bucket_index=0,
            highest_value=Decimal("50.00")
        ),
        budget_status=BudgetStatusResponse(
            buckets=[
                BudgetStatusBucketDto(spending=Decimal("50.00"), status=BudgetStatus.WITHIN, percentage=Decimal("50.00"), start_date=datetime(2026, 6, 19, tzinfo=timezone.utc))
            ],
            highest_spending=Decimal("50.00")
        ),
        top_categories=TopCategoriesResponse(
            total_spending=Decimal("50.00"),
            top_categories=[]
        )
    )
    
    service.stats_service.calculate_combined_stats.return_value = mock_stats_response
    service.stats_service._get_last_completed_bucket_start.return_value = datetime(2026, 6, 19)
    service.stats_service._get_next_bucket_start.return_value = datetime(2026, 6, 20)
    
    # Using timezone-aware datetimes for request model
    request = StatsRequest(
        user_id=user_id,
        granularity=Granularity.DAY,
        start_date=datetime(2026, 6, 19, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 21, tzinfo=timezone.utc)
    )
    
    # Execute the forecasting method
    res = service.forecast_buckets_combined(request)
    
    # Verify that stats_service was called with proper dates
    service.stats_service.calculate_combined_stats.assert_called_once()
    
    # Checking results
    assert isinstance(res, CombinedForecastResponse)
    assert len(res.financial_stats_forecast.buckets) >= 1

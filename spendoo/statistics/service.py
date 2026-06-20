from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
from decimal import Decimal
from typing import List, Dict
from collections import defaultdict

from spendoo.statistics.models import Granularity, FinancialStatsResponse, StatsBucketDto
from spendoo.statistics.repository import StatisticsRepository
from spendoo.core.models import BudgetORM

class StatisticsService:
    def __init__(self, db: Session):
        self.repo = StatisticsRepository(db)

    def calculate_stats(
        self,
        user_id: uuid.UUID,
        granularity: Granularity,
        start_date: datetime,
        end_date: datetime
    ) -> FinancialStatsResponse:
        # Normalize aware datetimes to naive to match database timestamps
        if start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)

        # 1. Generate Buckets
        buckets_ranges = self._generate_buckets(start_date, end_date, granularity)
        if not buckets_ranges:
            return FinancialStatsResponse(buckets=[], highest_spending_bucket_index=0)

        first_bucket_start = buckets_ranges[0]["start"]
        last_bucket_end = buckets_ranges[-1]["end"]

        # 2. Fetch data in single DB calls
        transactions = self.repo.get_transactions_in_range(user_id, first_bucket_start, last_bucket_end)
        budgets = self.repo.get_overlapping_budgets(user_id, first_bucket_start, last_bucket_end)

        # Group budgets by category
        budgets_by_category: Dict[uuid.UUID, List[BudgetORM]] = defaultdict(list)
        for b in budgets:
            budgets_by_category[b.category_id].append(b)

        # Sort transactions to allow a single-pass pointer aggregation (O(N log N + B) instead of O(N * B))
        sorted_tx = sorted(transactions, key=lambda x: x.transaction_date)
        tx_idx = 0
        num_tx = len(sorted_tx)

        # 3. Process each bucket
        bucket_dtos = []
        highest_spending_idx = 0
        max_spending = Decimal("-1.0")

        for b_idx, range_info in enumerate(buckets_ranges):
            k_start = range_info["start"]
            k_end = range_info["end"]

            # Compute spending and income in a single pointer-based pass
            spending = Decimal("0.0")
            income = Decimal("0.0")

            while tx_idx < num_tx and sorted_tx[tx_idx].transaction_date < k_start:
                tx_idx += 1

            while tx_idx < num_tx and sorted_tx[tx_idx].transaction_date < k_end:
                t = sorted_tx[tx_idx]
                amt = Decimal(str(t.amount))
                if amt < 0:
                    if t.category_id is not None:
                        spending += abs(amt)
                else:
                    income += amt
                tx_idx += 1

            # Compute budget for this bucket
            total_budget = Decimal("0.0")
            for cat_id, cat_budgets in budgets_by_category.items():
                total_budget += self._calculate_category_budget_for_bucket(
                    cat_budgets, k_start, k_end, granularity
                )

            b_dto = StatsBucketDto(
                spending=spending.quantize(Decimal("1.00")),
                income=income.quantize(Decimal("1.00")),
                budget=total_budget.quantize(Decimal("1.00")),
                start_date=k_start
            )
            bucket_dtos.append(b_dto)

            # Track highest spending bucket index on the fly
            if b_dto.spending > max_spending:
                max_spending = b_dto.spending
                highest_spending_idx = b_idx

        return FinancialStatsResponse(
            buckets=bucket_dtos,
            highest_spending_bucket_index=highest_spending_idx
        )

    def _generate_buckets(self, start: datetime, end: datetime, granularity: Granularity) -> List[Dict[str, datetime]]:
        # Align start date to bucket boundary
        if granularity == Granularity.DAY:
            first_start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == Granularity.WEEK:
            first_start = (start - timedelta(days=start.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == Granularity.MONTH:
            first_start = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif granularity == Granularity.YEAR:
            first_start = start.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            first_start = start.replace(hour=0, minute=0, second=0, microsecond=0)

        buckets = []
        curr_start = first_start
        while curr_start < end:
            if granularity == Granularity.DAY:
                curr_end = curr_start + timedelta(days=1)
            elif granularity == Granularity.WEEK:
                curr_end = curr_start + timedelta(weeks=1)
            elif granularity == Granularity.MONTH:
                if curr_start.month == 12:
                    curr_end = curr_start.replace(year=curr_start.year + 1, month=1, day=1)
                else:
                    curr_end = curr_start.replace(month=curr_start.month + 1, day=1)
            elif granularity == Granularity.YEAR:
                curr_end = curr_start.replace(year=curr_start.year + 1, month=1, day=1)
            else:
                curr_end = curr_start + timedelta(days=1)

            buckets.append({"start": curr_start, "end": curr_end})
            curr_start = curr_end

        return buckets

    def _calculate_category_budget_for_bucket(
        self,
        budgets: List[BudgetORM],
        k_start: datetime,
        k_end: datetime,
        granularity: Granularity
    ) -> Decimal:
        gran_level = self._get_granularity_level(granularity)
        bucket_days = (k_end.date() - k_start.date()).days
        if bucket_days <= 0:
            return Decimal("0.0")

        # Group overlapping budgets by relationship to granularity level
        downscaling_budgets = []
        same_level_budgets = []
        upscaling_budgets = []

        for b in budgets:
            # Check overlap
            intersect_days = self._calculate_intersecting_days(b.start_date, b.end_date, k_start, k_end)
            if intersect_days <= 0:
                continue

            b_level = self._get_period_level(b.period)
            if b_level > gran_level:
                downscaling_budgets.append((b, intersect_days))
            elif b_level == gran_level:
                same_level_budgets.append(b)
            else:
                upscaling_budgets.append((b, intersect_days))

        category_budget = Decimal("0.0")

        # Rule 1: Downscaling
        for b, intersect_days in downscaling_budgets:
            divisor = self._get_downscaling_divisor(b.period, granularity)
            base_amt = Decimal(str(b.amount)) / Decimal(str(divisor))
            category_budget += base_amt * (Decimal(str(intersect_days)) / Decimal(str(bucket_days)))

        # Rule 2: Same Level Overlap (Take the latest active configuration)
        if same_level_budgets:
            # Latest by start_date
            latest_budget = max(same_level_budgets, key=lambda x: x.start_date)
            category_budget += Decimal(str(latest_budget.amount))

        # Rule 3: Upscaling
        for b, intersect_days in upscaling_budgets:
            if b.period <= 0:
                continue
            daily_rate = Decimal(str(b.amount)) / Decimal(str(b.period))
            category_budget += daily_rate * Decimal(str(intersect_days))

        return category_budget

    def _calculate_intersecting_days(self, b_start: datetime, b_end: datetime, k_start: datetime, k_end: datetime) -> int:
        start = max(b_start, k_start)
        end = min(b_end, k_end)
        if start >= end:
            return 0
        return (end.date() - start.date()).days

    def _get_period_level(self, period_days: int) -> int:
        if period_days <= 1:
            return 1  # DAY
        if period_days <= 7:
            return 2  # WEEK
        if period_days <= 31:
            return 3  # MONTH
        return 4      # YEAR

    def _get_granularity_level(self, granularity: Granularity) -> int:
        if granularity == Granularity.DAY:
            return 1
        if granularity == Granularity.WEEK:
            return 2
        if granularity == Granularity.MONTH:
            return 3
        if granularity == Granularity.YEAR:
            return 4
        return 1

    def _get_downscaling_divisor(self, period: int, granularity: Granularity) -> float:
        b_level = self._get_period_level(period)
        if b_level == 4:  # YEAR
            if granularity == Granularity.MONTH:
                return 12.0
            if granularity == Granularity.WEEK:
                return 52.0
            if granularity == Granularity.DAY:
                return 365.0
        elif b_level == 3:  # MONTH
            if granularity == Granularity.WEEK:
                return max(1.0, float(period) / 7.0)
            if granularity == Granularity.DAY:
                return max(1.0, float(period))
        elif b_level == 2:  # WEEK
            if granularity == Granularity.DAY:
                return max(1.0, float(period))
        return max(1.0, float(period))

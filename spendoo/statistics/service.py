from sqlalchemy.orm import Session
from datetime import datetime, timezone, timezone, timedelta
import uuid
from decimal import Decimal
from typing import List, Dict
from collections import defaultdict

from spendoo.statistics.models import (
    Granularity,
    FinancialStatsResponse,
    StatsBucketDto,
    BudgetStatus,
    BudgetStatusBucketDto,
    BudgetStatusResponse,
    CategorySpendingDto,
    TopCategoriesResponse,
    CombinedStatsResponse
)
from spendoo.statistics.repository import StatisticsRepository
from spendoo.core.models import BudgetORM, TransactionORM


class StatisticsService:
    def __init__(self, db: Session):
        self.repo = StatisticsRepository(db)

    def calculate_stats(
        self,
        user_id: uuid.UUID,
        granularity: Granularity,
        start_date: datetime,
        end_date: datetime,
        category_id: uuid.UUID = None
    ) -> FinancialStatsResponse:
        start_date, end_date = self._normalize_dates(start_date, end_date)

        # 1. Generate Buckets
        buckets_ranges = self._generate_buckets(start_date, end_date, granularity)
        if not buckets_ranges:
            return FinancialStatsResponse(buckets=[], highest_spending_bucket_index=0, highest_value=Decimal("0.00"))

        first_bucket_start = buckets_ranges[0]["start"]
        last_bucket_end = buckets_ranges[-1]["end"]

        # 2. Fetch data in single DB calls
        transactions = self.repo.get_transactions_in_range(user_id, first_bucket_start, last_bucket_end, category_id)
        budgets = self.repo.get_overlapping_budgets(user_id, first_bucket_start, last_bucket_end, category_id)
        self._normalize_db_records(transactions, budgets)

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
        highest_value = Decimal("0.00")

        for b_idx, range_info in enumerate(buckets_ranges):
            k_start = range_info["start"]
            k_end = range_info["end"]

            spending, income, tx_idx, _ = self._aggregate_transactions_for_bucket(
                sorted_tx, tx_idx, k_start, k_end
            )

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
                start_date=k_start.replace(tzinfo=timezone.utc) if k_start.tzinfo is None else k_start
            )
            bucket_dtos.append(b_dto)

            # Track highest spending bucket index on the fly
            if b_dto.spending > max_spending:
                max_spending = b_dto.spending
                highest_spending_idx = b_idx

            # Track highest value (max of spending or income + budget) on the fly
            val = max(b_dto.spending, b_dto.income + b_dto.budget)
            if val > highest_value:
                highest_value = val

        return FinancialStatsResponse(
            buckets=bucket_dtos,
            highest_spending_bucket_index=highest_spending_idx,
            highest_value=highest_value
        )


    def _generate_buckets(
        self,
        start: datetime,
        end: datetime,
        granularity: Granularity,
        upper_bound: datetime = None
    ) -> List[Dict[str, datetime]]:
        if upper_bound is not None:
                        end = min(end, upper_bound)

        # Align start date to bucket boundary
        if granularity == Granularity.DAY:
            first_start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == Granularity.WEEK:
            days_to_subtract = (start.weekday() + 1) % 7
            first_start = (start - timedelta(days=days_to_subtract)).replace(hour=0, minute=0, second=0, microsecond=0)
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

    def calculate_budget_status(
        self,
        user_id: uuid.UUID,
        granularity: Granularity,
        start_date: datetime,
        end_date: datetime,
        now: datetime = None
    ) -> BudgetStatusResponse:
        start_date, end_date = self._normalize_dates(start_date, end_date)
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        

        # 1. Generate Buckets
        buckets_ranges = self._generate_buckets(start_date, end_date, granularity, now)
        if not buckets_ranges:
            return BudgetStatusResponse(buckets=[], highest_spending=Decimal("0.00"))

        first_bucket_start = buckets_ranges[0]["start"]
        last_bucket_end = buckets_ranges[-1]["end"]

        # 2. Fetch data in single DB calls
        transactions = self.repo.get_transactions_in_range(user_id, first_bucket_start, last_bucket_end)
        budgets = self.repo.get_overlapping_budgets(user_id, first_bucket_start, last_bucket_end)
        self._normalize_db_records(transactions, budgets)

        # Group budgets by category
        budgets_by_category: Dict[uuid.UUID, List[BudgetORM]] = defaultdict(list)
        for b in budgets:
            budgets_by_category[b.category_id].append(b)

        # Sort transactions for single-pass pointer aggregation
        sorted_tx = sorted(transactions, key=lambda x: x.transaction_date)
        tx_idx = 0
        num_tx = len(sorted_tx)

        bucket_dtos = []
        highest_spending = Decimal("0.00")

        for range_info in buckets_ranges:
            k_start = range_info["start"]
            k_end = range_info["end"]

            spending, income, tx_idx, _ = self._aggregate_transactions_for_bucket(
                sorted_tx, tx_idx, k_start, k_end
            )

            total_budget = Decimal("0.00")
            for cat_id, cat_budgets in budgets_by_category.items():
                total_budget += self._calculate_category_budget_for_bucket(
                    cat_budgets, k_start, k_end, granularity
                )

            # Use helper to calculate status and percentage
            percentage, status = self._determine_budget_status(spending, total_budget)

            b_dto = BudgetStatusBucketDto(
                spending=spending.quantize(Decimal("1.00")),
                status=status,
                percentage=percentage.quantize(Decimal("1.00")),
                start_date=k_start.replace(tzinfo=timezone.utc) if k_start.tzinfo is None else k_start
            )
            bucket_dtos.append(b_dto)

            if b_dto.spending > highest_spending:
                highest_spending = b_dto.spending

        return BudgetStatusResponse(
            buckets=bucket_dtos,
            highest_spending=highest_spending
        )

    def get_top_categories(
        self,
        user_id: uuid.UUID,
        granularity: Granularity,
        now: datetime = None
    ) -> TopCategoriesResponse:
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # ── Last completed bucket, not the current in-progress one ───────────────
        curr_start = self._get_last_completed_bucket_start(now, granularity)
        curr_end = now

        # ── Preceding bucket = one before the last completed ─────────────────────
        prev_start = self._get_preceding_start_date(curr_start, granularity)
        prev_end = curr_start

        # ── Fetch transactions for both windows ───────────────────────────────────
        tx_curr = self.repo.get_transactions_in_range(user_id, curr_start, curr_end)
        tx_prev = self.repo.get_transactions_in_range(user_id, prev_start, prev_end)
        self._normalize_db_records(tx_curr, [])
        self._normalize_db_records(tx_prev, [])

        # ── Aggregate current period ──────────────────────────────────────────────
        curr_spending_by_cat = defaultdict(Decimal)
        total_spending = Decimal("0.00")
        for t in tx_curr:
            amt = Decimal(str(t.amount))
            if amt < 0 and t.category_id is not None:
                curr_spending_by_cat[t.category_id] += abs(amt)
                total_spending += abs(amt)

        # ── Aggregate preceding period ────────────────────────────────────────────
        prev_spending_by_cat = defaultdict(Decimal)
        for t in tx_prev:
            amt = Decimal(str(t.amount))
            if amt < 0 and t.category_id is not None:
                prev_spending_by_cat[t.category_id] += abs(amt)

        top_categories = self._build_top_categories(user_id, curr_spending_by_cat, prev_spending_by_cat)

        return TopCategoriesResponse(
            total_spending=total_spending.quantize(Decimal("1.00")),
            top_categories=top_categories
        )
    
    def calculate_combined_stats(
        self,
        user_id: uuid.UUID,
        granularity: Granularity,
        start_date: datetime,
        end_date: datetime,
        now: datetime = None
    ) -> CombinedStatsResponse:
        start_date, end_date = self._normalize_dates(start_date, end_date)
        # 1. Generate Buckets
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        

        buckets_ranges = self._generate_buckets(start_date, end_date, granularity)

        if not buckets_ranges:
            return CombinedStatsResponse(
                financial_stats=FinancialStatsResponse(buckets=[], highest_spending_bucket_index=0, highest_value=Decimal("0.00")),
                budget_status=BudgetStatusResponse(buckets=[], highest_spending=Decimal("0.00")),
                top_categories=TopCategoriesResponse(total_spending=Decimal("0.00"), top_categories=[])
            )

        first_bucket_start = buckets_ranges[0]["start"]
        last_bucket_end = buckets_ranges[-1]["end"]

        # 2. Determine preceding bucket range for category percentage change
        # preceding period = one bucket before the last completed bucket
        last_completed_start  = self._get_last_completed_bucket_start(now, granularity)
        last_completed_end = min(end_date, now)
        preceding_start = self._get_preceding_start_date(last_completed_start, granularity)
        preceding_end = last_completed_start   # the bucket just before the last completed one

        # 3. Fetch data in single DB calls
        fetch_start = min(preceding_start, first_bucket_start)
        fetch_end = max(last_completed_end, last_bucket_end)
        transactions = self.repo.get_transactions_in_range(user_id, fetch_start, fetch_end)
        budgets = self.repo.get_overlapping_budgets(user_id, first_bucket_start, last_bucket_end)
        self._normalize_db_records(transactions, budgets)

        # Group budgets by category
        budgets_by_category: Dict[uuid.UUID, List[BudgetORM]] = defaultdict(list)
        for b in budgets:
            budgets_by_category[b.category_id].append(b)

        # Sort transactions for single-pass pointer aggregation
        sorted_tx = sorted(transactions, key=lambda x: x.transaction_date)

        # Calculate category spending specifically for the last completed bucket and the preceding bucket
        curr_spending_by_cat = defaultdict(Decimal)
        prev_spending_by_cat = defaultdict(Decimal)
        for t in sorted_tx:
            dt = t.transaction_date
            amt = Decimal(str(t.amount))
            if amt < 0 and t.category_id is not None:
                if last_completed_start <= dt < last_completed_end:
                    curr_spending_by_cat[t.category_id] += abs(amt)
                elif preceding_start <= dt < preceding_end:
                    prev_spending_by_cat[t.category_id] += abs(amt)

        # 4. Process each bucket
        stats_bucket_dtos = []
        status_bucket_dtos = []
        highest_spending_idx = 0
        max_spending = Decimal("-1.0")
        highest_value = Decimal("0.00")
        highest_spending = Decimal("0.00")

        tx_idx = 0
        for b_idx, range_info in enumerate(buckets_ranges):
            k_start = range_info["start"]
            k_end = range_info["end"]

            spending, income, tx_idx, _ = self._aggregate_transactions_for_bucket(
                sorted_tx, tx_idx, k_start, k_end, track_category_spending=False
            )

            total_budget = Decimal("0.00")
            for cat_id, cat_budgets in budgets_by_category.items():
                total_budget += self._calculate_category_budget_for_bucket(
                    cat_budgets, k_start, k_end, granularity
                )

            # --- Financial Stats Bucket ---
            fs_dto = StatsBucketDto(
                spending=spending.quantize(Decimal("1.00")),
                income=income.quantize(Decimal("1.00")),
                budget=total_budget.quantize(Decimal("1.00")),
                start_date=k_start.replace(tzinfo=timezone.utc) if k_start.tzinfo is None else k_start
            )
            stats_bucket_dtos.append(fs_dto)

            # Track highest spending bucket index for financial stats
            if fs_dto.spending > max_spending:
                max_spending = fs_dto.spending
                highest_spending_idx = b_idx

            # Track highest value (max of spending or income + budget) on the fly
            val = max(fs_dto.spending, fs_dto.income + fs_dto.budget)
            if val > highest_value:
                highest_value = val

            # --- Budget Status Bucket ---
            if k_start < now:
                percentage, status = self._determine_budget_status(spending, total_budget)
                bs_dto = BudgetStatusBucketDto(
                    spending=spending.quantize(Decimal("1.00")),
                    status=status,
                    percentage=percentage.quantize(Decimal("1.00")),
                    start_date=k_start.replace(tzinfo=timezone.utc) if k_start.tzinfo is None else k_start
                )
                status_bucket_dtos.append(bs_dto)

                # Track highest spending for budget status
                if bs_dto.spending > highest_spending:
                    highest_spending = bs_dto.spending


        # 5. Build Top Categories response using DRY helper
        top_categories = self._build_top_categories(user_id, curr_spending_by_cat, prev_spending_by_cat)

        return CombinedStatsResponse(
            financial_stats=FinancialStatsResponse(
                buckets=stats_bucket_dtos,
                highest_spending_bucket_index=highest_spending_idx,
                highest_value=highest_value
            ),
            budget_status=BudgetStatusResponse(
                buckets=status_bucket_dtos,
                highest_spending=highest_spending
            ),
            top_categories=TopCategoriesResponse(
                total_spending=sum(curr_spending_by_cat.values(), Decimal("0.00")).quantize(Decimal("1.00")),
                top_categories=top_categories
            )
        )

    def _normalize_dates(self, start_date: datetime, end_date: datetime) -> tuple[datetime, datetime]:
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        return start_date, end_date

    def _determine_budget_status(self, spending: Decimal, total_budget: Decimal) -> tuple[Decimal, BudgetStatus]:
        if total_budget > 0:
            percentage = (spending / total_budget) * Decimal("100.00")
        else:
            percentage = Decimal("100.00") if spending > 0 else Decimal("0.00")

        if percentage < Decimal("90.00"):
            status = BudgetStatus.WITHIN
        elif percentage <= Decimal("100.00"):
            status = BudgetStatus.RISK
        else:
            status = BudgetStatus.OVERSPEND
        return percentage, status

    def _get_preceding_start_date(self, start_date: datetime, granularity: Granularity) -> datetime:
        if granularity == Granularity.DAY:
            return start_date - timedelta(days=1)
        if granularity == Granularity.WEEK:
            return start_date - timedelta(weeks=1)
        if granularity == Granularity.MONTH:
            if start_date.month == 1:
                return start_date.replace(year=start_date.year - 1, month=12, day=1)
            else:
                return start_date.replace(month=start_date.month - 1, day=1)
        if granularity == Granularity.YEAR:
            return start_date.replace(year=start_date.year - 1)
        return start_date - timedelta(days=1)

    def _build_top_categories(
        self,
        user_id: uuid.UUID,
        curr_spending: Dict[uuid.UUID, Decimal],
        prev_spending: Dict[uuid.UUID, Decimal]
    ) -> List[CategorySpendingDto]:
        categories = self.repo.get_user_categories(user_id)
        cat_map = {c.id: c for c in categories}

        total_spending = sum(curr_spending.values(), Decimal("0.00"))

        cat_dtos = []
        for cat_id, curr_val in curr_spending.items():
            prev_val = prev_spending.get(cat_id, Decimal("0.00"))
            
            if prev_val > 0:
                pct_change = ((curr_val - prev_val) / prev_val) * Decimal("100.00")
            else:
                pct_change = Decimal("100.00") if curr_val > 0 else Decimal("0.00")

            if total_spending > 0:
                contrib_pct = (curr_val / total_spending) * Decimal("100.00")
            else:
                contrib_pct = Decimal("0.00")

            cat_info = cat_map.get(cat_id)
            cat_name = cat_info.category_name if cat_info else "Unknown"
            cat_icon = cat_info.category_icon if (cat_info and cat_info.category_icon) else "default"

            dto = CategorySpendingDto(
                category_id=cat_id,
                category_name=cat_name,
                category_icon=cat_icon,
                spending=curr_val.quantize(Decimal("1.00")),
                percentage_change=pct_change.quantize(Decimal("1.00")),
                contribution_percentage=contrib_pct.quantize(Decimal("1.00"))
            )
            cat_dtos.append(dto)

        cat_dtos.sort(key=lambda x: x.spending, reverse=True)
        return cat_dtos[:6]

    def _aggregate_transactions_for_bucket(
        self,
        sorted_tx: List[TransactionORM],
        tx_idx: int,
        k_start: datetime,
        k_end: datetime,
        track_category_spending: bool = False
    ) -> tuple[Decimal, Decimal, int, Dict[uuid.UUID, Decimal]]:
        num_tx = len(sorted_tx)
        spending = Decimal("0.00")
        income = Decimal("0.00")
        curr_spending_by_cat = defaultdict(Decimal)

        while tx_idx < num_tx and sorted_tx[tx_idx].transaction_date < k_start:
            tx_idx += 1

        while tx_idx < num_tx and sorted_tx[tx_idx].transaction_date < k_end:
            t = sorted_tx[tx_idx]
            amt = Decimal(str(t.amount))
            if amt < 0 and t.category_id is not None:
                spending += abs(amt)
                if track_category_spending:
                    curr_spending_by_cat[t.category_id] += abs(amt)
            else:
                income += amt
            tx_idx += 1

        return spending, income, tx_idx, curr_spending_by_cat
    
    def _get_next_bucket_start(self, bucket_start: datetime, granularity: Granularity) -> datetime:
        """Returns the start of the bucket immediately after the given one."""
        if granularity == Granularity.DAY:
            return bucket_start + timedelta(days=1)
        elif granularity == Granularity.WEEK:
            return bucket_start + timedelta(weeks=1)
        elif granularity == Granularity.MONTH:
            if bucket_start.month == 12:
                return bucket_start.replace(year=bucket_start.year + 1, month=1, day=1)
            return bucket_start.replace(month=bucket_start.month + 1, day=1)
        elif granularity == Granularity.YEAR:
            return bucket_start.replace(year=bucket_start.year + 1)
        return bucket_start + timedelta(days=1)
    
    def _get_last_completed_bucket_start(self, now: datetime, granularity: Granularity) -> datetime:
        """Identical to the one in ForecastService — finds the last fully completed bucket."""
        if granularity == Granularity.DAY:
            return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == Granularity.WEEK:
            days_since_sunday = (now.weekday() + 1) % 7
            current_week_start = (now - timedelta(days=days_since_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
            return current_week_start - timedelta(weeks=1)
        elif granularity == Granularity.MONTH:
            if now.month == 1:
                return now.replace(year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
            return now.replace(month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif granularity == Granularity.YEAR:
            return now.replace(year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    def _normalize_db_records(
        self,
        transactions: List[TransactionORM],
        budgets: List[BudgetORM]
    ) -> None:
        for t in transactions:
            if t.transaction_date and t.transaction_date.tzinfo is None:
                t.transaction_date = t.transaction_date.replace(tzinfo=timezone.utc)
        for b in budgets:
            if b.start_date and b.start_date.tzinfo is None:
                b.start_date = b.start_date.replace(tzinfo=timezone.utc)
            if b.end_date and b.end_date.tzinfo is None:
                b.end_date = b.end_date.replace(tzinfo=timezone.utc)



from .calculate_stats import CalculateStatsTool
from .calculate_budget_status import CalculateBudgetStatusTool
from .get_top_categories import GetTopCategoriesTool

from .forecast_stats import ForecastStatsTool
from .get_user_info import GetUserInfoTool
from .get_transactions import GetTransactionsTool
from .get_categories import GetCategoriesTool
from .get_budgets import GetBudgetsTool
from .get_scheduled_payments import GetScheduledPaymentsTool
from .get_saving_goals import GetSavingGoalsTool
from .get_achievements import GetAchievementsTool
from .get_notifications import GetNotificationsTool

from .get_balance_summary import GetBalanceSummaryTool
from .get_categories_summary import GetCategoriesSummaryTool
from .get_scheduled_payments_summary import GetScheduledPaymentsSummaryTool
from .get_saving_goals_summary import GetSavingGoalsSummaryTool
from .get_top_spending_categories import GetTopSpendingCategoriesTool
from .get_top_frequency_items import GetTopFrequencyItemsTool

# Register available tools here
AVAILABLE_TOOLS = [
    CalculateStatsTool(),
    CalculateBudgetStatusTool(),
    GetTopCategoriesTool(),
    ForecastStatsTool(),
    GetUserInfoTool(),
    GetTransactionsTool(),
    GetCategoriesTool(),
    GetBudgetsTool(),
    GetScheduledPaymentsTool(),
    GetSavingGoalsTool(),
    GetAchievementsTool(),
    GetNotificationsTool(),
    GetBalanceSummaryTool(),
    GetCategoriesSummaryTool(),
    GetScheduledPaymentsSummaryTool(),
    GetSavingGoalsSummaryTool(),
    GetTopSpendingCategoriesTool(),
    GetTopFrequencyItemsTool()
]

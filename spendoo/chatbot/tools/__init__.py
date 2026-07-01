from .calculate_stats import CalculateStatsTool
from .calculate_budget_status import CalculateBudgetStatusTool
from .get_top_categories import GetTopCategoriesTool

# Register available tools here
AVAILABLE_TOOLS = [
    CalculateStatsTool(),
    CalculateBudgetStatusTool(),
    GetTopCategoriesTool()
]

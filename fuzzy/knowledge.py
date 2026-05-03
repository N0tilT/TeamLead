from typing import Dict, List

TASK_TYPE_WEIGHTS: Dict[str, float] = {
    "feature": 1.0,
    "bugfix": 0.8,
    "tech_debt": 1.2,
    "docs": 0.6
}

MITIGATION_STRATEGIES: Dict[str, List[str]] = {
    "Low": ["standard_review"],
    "Medium": ["add_tests", "peer_review"],
    "High": ["spike", "pair_programming", "add_tests"],
    "Critical": ["prototype", "refactor_prereq", "daily_sync"]
}
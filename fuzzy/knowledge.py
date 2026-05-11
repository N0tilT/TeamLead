TASK_TYPE_WEIGHTS = {
    "feature": 1.0,
    "bugfix": 0.7,
    "refactor": 0.8,
    "research": 1.2
}

MITIGATION_STRATEGIES = {
    "Low": ["Standard sprint planning", "Pair programming optional"],
    "Medium": ["Code review mandatory", "Break into subtasks", "Add monitoring"],
    "High": ["Architecture review", "Dedicated QA resource", "Phased rollout"],
    "Critical": ["Executive approval required", "Dedicated task force", "Rollback plan mandatory"]
}
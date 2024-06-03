from enum import StrEnum


class TestTaskQueues(StrEnum):
    MAIN = "MAIN_TASK_QUEUE"
    HIGH_PRIORITY = "HIGH_PRIORITY_TASK_QUEUE"

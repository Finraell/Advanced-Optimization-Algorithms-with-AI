"""Background worker tasks.

This module defines a Celery app and a sample task.  Real implementations
would include tasks for compiling optimisation models, executing solvers,
posting webhooks and computing AI recommendations.  The broker URL and
result backend are expected to be configured via environment variables.
"""

from celery import Celery
import os

broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
result_backend = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("advanced_optimization_worker", broker=broker_url, backend=result_backend)


@celery_app.task
def solve_stub(run_id: str) -> dict:
    """A placeholder task that pretends to solve an optimisation problem.

    In reality this would call solver adapters and update the database.
    """
    # Simulate some computation
    import time
    time.sleep(2)
    return {"run_id": run_id, "status": "succeeded", "objective_value": 123.45}

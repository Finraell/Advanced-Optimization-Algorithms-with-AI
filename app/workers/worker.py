"""Background worker tasks.

This module defines a Celery app and a sample task.  Real implementations
would include tasks for compiling optimisation models, executing solvers,
posting webhooks and computing AI recommendations.  The broker URL and
result backend are expected to be configured via environment variables.
"""

from celery import Celery
import os

# Import the solver dispatcher from solve.py.  This import is optional and
# guarded in case the solvers are not installed.  If unavailable, the
# ``solve_model_task`` will raise at runtime when invoked.
try:
    from .solve import solve_model  # type: ignore
except Exception:
    solve_model = None  # type: ignore


broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
result_backend = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("advanced_optimization_worker", broker=broker_url, backend=result_backend)


@celery_app.task
def solve_stub(run_id: str) -> dict:
    """Deprecated placeholder task.

    This task simulates solving an optimisation problem by sleeping for two
    seconds and returning a stub result.  It remains for backward
    compatibility and should not be used for new functionality.
    """
    import time
    time.sleep(2)
    return {"run_id": run_id, "status": "succeeded", "objective_value": 123.45}


@celery_app.task
def solve_model_task(run_id: str, model_json: dict, solver: str | None = None, params: dict | None = None) -> dict:
    """Solve an optimisation model using the strategy pattern and return the result.

    This task delegates to the ``solve_model`` function defined in
    ``app/workers/solve.py``.  It expects a parsed model JSON (e.g. as
    returned by the AI translation endpoint), an optional explicit solver
    name, and solver ‑specific parameters.  The task stores and returns
    the solver result dictionary.  In a real implementation this would
    also persist results to the database and object storage, and emit
    webhook events.

    Args:
        run_id: Identifier for the run to which this solve corresponds.
        model_json: The optimisation model definition.
        solver: Optional solver name (e.g. "ortools", "cvxpy", "pyomo").
        params: Optional parameters to pass through to the solver.

    Returns:
        A dictionary with solver status, objective value, variable assignments
        and logs.
    """
    if solve_model is None:
        raise RuntimeError("Solver adapters are not available. Ensure optional dependencies are installed.")

    result = solve_model(model_json, solver=solver, params=params or {})
    # Attach the run_id to the result for traceability
    result["run_id"] = run_id
    return result

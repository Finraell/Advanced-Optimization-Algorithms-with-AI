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


@celery_app.task(name="tasks.solve_model_task")
def solve_model_task(run_id: str, model_json: dict, solver: str | None = None, params: dict | None = None) -> dict:
    """Solve an optimisation model using the strategy pattern and persist state.

    This task updates the corresponding ``Run`` record in the database
    throughout its lifecycle: it marks the run as ``running`` at the
    beginning, records start and finish timestamps, and stores solver
    results when complete.  If solver adapters are unavailable, a
    ``RuntimeError`` is raised immediately.

    Args:
        run_id: Identifier for the run (as a string representation of the integer primary key).
        model_json: The optimisation model definition.
        solver: Optional solver name (e.g. "ortools", "cvxpy", "pyomo").
        params: Optional solver parameters.

    Returns:
        A dictionary with solver status, objective value, variable assignments and logs.
    """
    if solve_model is None:
        raise RuntimeError("Solver adapters are not available. Ensure optional dependencies are installed.")

    # Import database components lazily to avoid circular imports
    from ..api.database import SessionLocal  # type: ignore
    from ..api import models  # type: ignore
    import datetime as _dt

    session = SessionLocal()
    # Parse run_id to integer primary key
    try:
        run_pk = int(run_id.replace("run_", "")) if isinstance(run_id, str) and run_id.startswith("run_") else int(run_id)
    except Exception:
        run_pk = None

    try:
        # Update run status to running
        if run_pk is not None:
            run = session.query(models.Run).filter(models.Run.id == run_pk).first()
            if run:
                run.status = "running"
                run.started_at = _dt.datetime.utcnow()
                session.commit()

        # Execute the solver
        result = solve_model(model_json, solver=solver, params=params or {})
        result["run_id"] = run_id

        # Persist result status
        if run_pk is not None:
            run = session.query(models.Run).filter(models.Run.id == run_pk).first()
            if run:
                run.status = result.get("status", "succeeded")
                run.objective_value = result.get("objective_value")
                run.finished_at = _dt.datetime.utcnow()
                session.commit()

        return result
    finally:
        session.close()

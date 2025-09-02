import logging
import os
from contextlib import contextmanager
from typing import Any, Optional, Tuple, Union
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from eflips.model import Scenario
import matplotlib.pyplot as plt
import numpy as np
@contextmanager
def create_session(
    scenario: Union[Scenario, int, Any], database_url: Optional[str] = None
) -> Tuple[Session, Scenario]:
    """
    Create a valid session from various inputs.

    This method takes a scenario, which can be either a :class:`eflips.model.Scenario` object, an integer specifying
    the ID of a scenario in the database, or any other object that has an attribute `id` that is an integer. It then
    creates a SQLAlchemy session and returns it. If the scenario is a :class:`eflips.model.Scenario` object, the
    session is created and returned. If the scenario is an integer or an object with an `id` attribute, the session
    is created, returned and closed after the context manager is exited.

    :param scenario: Either a :class:`eflips.model.Scenario` object, an integer specifying the ID of a scenario in the
        database, or any other object that has an attribute `id` that is an integer.
    :return: Yield a Tuple of the session and the scenario.
    """
    logger = logging.getLogger(__name__)

    managed_session = False
    engine = None
    session = None
    try:
        if isinstance(scenario, Scenario):
            session = inspect(scenario).session
        elif isinstance(scenario, int) or hasattr(scenario, "id"):
            logger.warning(
                "Scenario passed was not part of an active session. Uncommited changes will be ignored."
            )

            if isinstance(scenario, int):
                scenario_id = scenario
            else:
                scenario_id = scenario.id

            if database_url is None:
                if "DATABASE_URL" in os.environ:
                    database_url = os.environ.get("DATABASE_URL")
                else:
                    raise ValueError("No database URL specified.")

            managed_session = True
            engine = create_engine(database_url)
            session = Session(engine)
            scenario = session.query(Scenario).filter(Scenario.id == scenario_id).one()
        else:
            raise ValueError(
                "The scenario parameter must be either a Scenario object, an integer or object with an 'id' attribute."
            )
        yield session, scenario
    finally:
        if managed_session:
            if session is not None:
                session.commit()
                session.close()
            if engine is not None:
                engine.dispose()


def plot_tco_comparison(all_tco: list[dict], all_names: list[str], colors) -> plt.Figure:
    # Collect all possible keys
    all_keys = sorted({k for d in all_tco for k in d.keys()})

    # Convert dicts to aligned arrays
    values = np.array([[d.get(k, 0) for k in all_keys] for d in all_tco])

    # Plot
    fig, ax = plt.subplots(figsize=(15, 10), constrained_layout=True)

    x = np.arange(len(all_tco))
    bottom = np.zeros(len(all_tco))

    for i, key in enumerate(all_keys):
        current_bar = ax.bar(x, values[:, i], bottom=bottom, label=key, color=colors[key])
        bottom += values[:, i]
        ax.bar_label(current_bar, label_type="center", padding=3, fmt="%.2f")

    totals = values.sum(axis=1)
    for xi, total in zip(x, totals):
        ax.text(round(xi, 2), total + 0.3, str(round(total, 2)), ha="center", va="bottom", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([all_names[i] for i in range(len(all_tco))])
    ax.set_ylabel("Value")
    ax.legend(title="Keys", loc="upper left", bbox_to_anchor=(1.05, 1))
    return fig
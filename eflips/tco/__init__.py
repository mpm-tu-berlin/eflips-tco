from eflips.tco.data_queries import init_tco_parameters
from eflips.tco.tco_calculator import TCOCalculator

from typing import Union, Optional, Any, Dict
from eflips.model import Scenario
from eflips.tco.util import create_session
import logging


def calculate_tco(scenario: Union[Scenario, int, Any],
                  database_url: Optional[str] = None) -> Dict[str, float]:
    """
    This function calculates the Total Cost of Ownership (TCO) for a given scenario and returns a dictionary
    with the TCO values categorized by type. If there is an error during the calculation, it returns a dictionary
    with dummy data.

    :param scenario: Either a :class:`eflips.model.Scenario` object or an integer specifying the ID of a scenario in the
        database.
    :param database_url: Optional database URL to connect to if the scenario is provided as an integer.
    :return: A dictionary with TCO values categorized by type.

    """
    logger = logging.getLogger(__name__)
    with create_session(scenario, database_url) as (session, scenario):
        if isinstance(scenario, int):
            scenario = session.query(Scenario).filter(Scenario.id == scenario).one()
        elif not isinstance(scenario, Scenario):
            raise ValueError("scenario must be either an integer or a Scenario object")

        try:
            tco_calculator = TCOCalculator(scenario, energy_consumption_mode="constant")
        except Exception as e:
            logger.warning("Error in initializing TCOCalculator: %s. Returning dummy data instead", e)

            return {
                "INFRASTRUCTURE": 1.0,
                "STAFF": 1.0,
                "BATTERY": 1.0,
                "MAINTENANCE": 1.0,
                "VEHICLE": 1.0,
                "OTHER": 1.0,
                "ENERGY": 1.0
            }

        tco_calculator.calculate()
        result = tco_calculator.tco_by_type
        result["INFRASTRUCTURE"] += result.get("CHARGING_POINT", 0.0)
        result.pop("CHARGING_POINT", None)
        return result

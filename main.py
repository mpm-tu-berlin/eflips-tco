#!/usr/bin/env python3

"""
This is the main module of the project. It should contain the main entry point of the project. By
running this, the essential functionality of the project should be executed.
"""

from eflips.tco.data_queries import init_tco_parameters
from eflips.tco.default_params import get_params_from_file
from pathlib import Path
import os

# Environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")
SCENARIO_ID = 3
from eflips.tco.tco_calculator import TCOCalculator


if __name__ == "__main__":

    defaults = get_params_from_file(Path(__file__).parent / "eflips" / "tco" / "default_params" / "berlin_bvg.py")

    init_tco_parameters(
        scenario=SCENARIO_ID,
        database_url=DATABASE_URL,
        scenario_params=defaults.SCENARIO_TCO,
        vehicle_type_params=defaults.VEHICLE_TYPES,
        battery_type_params=defaults.BATTERY_TYPES,
        charging_point_type_params=defaults.CHARGING_POINT_TYPES,
        charging_infra_params=defaults.CHARGING_INFRASTRUCTURE,
    )

    tco_calculator = TCOCalculator(
        scenario=SCENARIO_ID,
        database_url=DATABASE_URL,
        energy_consumption_mode="constant",
    )

    tco_calculator.calculate()

    print(tco_calculator.tco_unit_distance)
    tco_calculator.visualize()

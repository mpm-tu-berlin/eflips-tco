#!/usr/bin/env python3

"""
This is the main module of the project. It should contain the main entry point of the project. By
running this, the essential functionality of the project should be executed.
"""

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from eflips.model import Scenario

import os
import json

import parameters as p
import tco_utils as f
import data_queries as gd
from analysis import (
    plot_scenarios,
    sensitivity_analysis,
    plot_efficiency,
    plot_scenario_info,
)
from init_database import init_database

# Environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")
# DATABASE_URL = 'postgresql://julian:password@localhost/eflips_tco'
# SCENARIO_ID = os.environ.get('SCENARIO_ID')
SCENARIO_ID = 1
INPUT_FILE = os.environ.get("INPUT_FILE")  # 'input_tco.csv' in this case
INCLUDE_DETAILED_ANALYSIS = os.environ.get("INCLUDE_DETAILED_ANALYSIS")
from eflips.tco.tco_calculator import TCOCalculator

# unzstd --long=31 results_for_tco.sql.zst --stdout | psql eflips_tco um DB neu zu laden. Erst alle Tabellen außer spatial_ref_sys auswählen und löschen (mit entf)!


if __name__ == "__main__":

    tco_calculator_s1 = TCOCalculator(scenario_id=SCENARIO_ID, database_url=DATABASE_URL)
    tco_calculator_s1.calculate()

    print(tco_calculator_s1.tco_per_distance)


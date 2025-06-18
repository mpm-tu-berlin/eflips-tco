#!/usr/bin/env python3

"""
This is the main module of the project. It should contain the main entry point of the project. By
running this, the essential functionality of the project should be executed.
"""

from eflips.tco.data_queries import init_tco_parameters
import os
import json


# Environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")
SCENARIO_ID = 4
from eflips.tco.tco_calculator import TCOCalculator


if __name__ == "__main__":

    # initialize the database if there are no tco parameters

    vehicle_types = {
        18: {
            "name": "Ebusco 3.0 12 large battery",
            "useful_life": 12,
            "procurement_cost": 370000.0,
            "cost_escalation": 0.025,
        },
        19: {
            "name": "Solaris Urbino 18 large battery",
            "useful_life": 12,
            "procurement_cost": 603000.0,
            "cost_escalation": 0.025,
        },
        20: {
            "name": "Alexander Dennis Enviro500EV large battery",
            "useful_life": 12,
            "procurement_cost": 700000.0,
            "cost_escalation": 0.025,
        },
    }

    battery_types = {
        10: {
            "name": "Ebusco 3.0 12 large battery",
            "procurement_cost": 350,
            "useful_life": 6,
            "cost_escalation": -0.03,
        },
        11: {
            "name": "Ebusco 3.0 12 large battery",
            "procurement_cost": 350,
            "useful_life": 6,
            "cost_escalation": -0.03,
        },
        12: {
            "name": "Ebusco 3.0 12 small battery",
            "procurement_cost": 350,
            "useful_life": 6,
            "cost_escalation": -0.03,
        },
    }

    charging_point_types = {
        "depot": {
            "name": "Depot Charging Point",
            "procurement_cost": 100000.0,
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
        "opportunity": {
            "name": "Opportunity Charging Point",
            "procurement_cost": 275000.0,
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
    }

    charging_infrastructure = {
        "depot": {
            "name": "Depot Charging Infrastructure",
            "procurement_cost": 3400000.0,
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
        "station": {
            "name": "Opportunity Charging Infrastructure",
            "procurement_cost": 500000.0,
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
    }

    init_tco_parameters(
        scenario_id=SCENARIO_ID,
        database_url=DATABASE_URL,
        vehicle_types=vehicle_types,
        battery_types=battery_types,
        charging_point_types=charging_point_types,
        charging_infrastructure=charging_infrastructure,
    )

    tco_calculator_s1 = TCOCalculator(
        scenario_id=SCENARIO_ID, database_url=DATABASE_URL
    )

    tco_calculator_s1.calculate()

    print(tco_calculator_s1.tco_per_distance)
    tco_calculator_s1.visualize()

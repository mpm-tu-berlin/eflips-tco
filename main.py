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

    vehicle_types = [
        {
            "id": 18,
            "name": "Ebusco 3.0 12 large battery",
            "useful_life": 14,
            "procurement_cost": 340000.0,
            "cost_escalation": 0.02,
        },
        {
            "id": 19,
            "name": "Solaris Urbino 18 large battery",
            "useful_life": 14,
            "procurement_cost": 603000.0,
            "cost_escalation": 0.02,
        },
        {
            "id": 20,
            "name": "Alexander Dennis Enviro500EV large battery",
            "useful_life": 14,
            "procurement_cost": 650000.0,
            "cost_escalation": 0.02,
        },
    ]

    battery_types = [
        {
            "name": "Ebusco 3.0 12 and 18 large battery",
            "procurement_cost": 315,
            "useful_life": 7,
            "cost_escalation": -0.03,
            "vehicle_type_ids": [18, 20]
            # "id": 67,
        },
        {
            "name": "Solaris Urbino 18 large battery",
            "procurement_cost": 285,
            "useful_life": 7,
            "cost_escalation": -0.03,
            "vehicle_type_ids": [19],
            # "id": 68,
        },
        # {
        #     "name": "Alexander Dennis Enviro500EV large battery",
        #     "procurement_cost": 315,
        #     "useful_life": 7,
        #     "cost_escalation": -0.03,
        #     "vehicle_type_id": 20,
        #     # "id": 69,
        # },
    ]

    charging_point_types = [
        {
            "type": "depot",
            "name": "Depot Charging Point",
            "procurement_cost": 100000.0,
            "useful_life": 20,
            "cost_escalation": 0.02,
            # "id": 50,
        },
        {
            "type": "opportunity",
            "name": "Opportunity Charging Point",
            "procurement_cost": 275000.0,
            "useful_life": 20,
            "cost_escalation": 0.02,
            # "id": 51,
        },
    ]

    charging_infrastructure = [
        {
            "type": "depot",
            "name": "Depot Charging Infrastructure",
            "procurement_cost": 3400000.0,
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
        {
            "type": "station",
            "name": "Opportunity Charging Infrastructure",
            "procurement_cost": 500000.0,
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
    ]

    scenario_tco_parameters = {
        "project_duration": 20,
        "interest_rate": 0.04,
        "inflation_rate": 0.02,
        "staff_cost": 25.0,  # calculated: 35,000 € p.a. per driver/1600 h p.a. per driver
        # Fuel cost in EUR per unit fuel
        "fuel_cost": 0.1794,  # electricity cost
        # Maintenance cost in EUR per km
        "maint_cost": 0.35,
        # Maintenance cost infrastructure per year and charging slot
        "maint_infr_cost": 1000,
        # Taxes and insurance cost in EUR per year and bus
        "taxes": 278,
        "insurance": 9693,  # DCO #9703, # EBU
        # Cost escalation factors (cef / pef)
        "pef_general": 0.02,
        "pef_wages": 0.025,
        "pef_fuel": 0.038,
        "pef_insurance": 0.02,
    }

    tco_params = {
        "vehicle_types": vehicle_types,
        "battery_types": battery_types,
        "charging_point_types": charging_point_types,
        "charging_infrastructure": charging_infrastructure,
        "scenario_tco_parameters": scenario_tco_parameters,
    }

    tco_calculator_s1 = TCOCalculator(
        scenario=SCENARIO_ID, database_url=DATABASE_URL, tco_parameters=tco_params
    )

    tco_calculator_s1.calculate()

    # Something like:
    # tco_params = {...}
    # tco_calculator_s1 = TCOCalculator(scenario_id=SCENARIO_ID, database_url=DATABASE_URL, tco_params=tco_params)
    # tco_calculator_s1.calculate()

    print(tco_calculator_s1.tco_per_distance)
    tco_calculator_s1.visualize()

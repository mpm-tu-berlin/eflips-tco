#!/usr/bin/env python3

"""
This is the main module of the project. It should contain the main entry point of the project. By
running this, the essential functionality of the project should be executed.
"""

from eflips.tco.data_queries import init_tco_parameters
import os

# Environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")
SCENARIO_ID = 3
from eflips.tco.tco_calculator import TCOCalculator


if __name__ == "__main__":

    # initialize the database if there are no tco parameters

    vehicle_types = [
        {
            "id": 15,
            "name": "Ebusco 3.0 12 large battery",
            "useful_life": 14,
            "procurement_cost": 580000.0,
            "cost_escalation": 0.02,
            "const_energy_consumption": 1.48,
            "procurement_cost_diesel": 250000.0,
        },
        {
            "id": 16,
            "name": "Solaris Urbino 18 large battery",
            "useful_life": 14,
            "procurement_cost": 780000.0,
            "cost_escalation": 0.02,
            "const_energy_consumption": 2.16,
            "procurement_cost_diesel": 300000.0,
        },
        {
            "id": 17,
            "name": "Alexander Dennis Enviro500EV large battery",
            "useful_life": 14,
            "procurement_cost": 780000.0,
            "cost_escalation": 0.02,
            "const_energy_consumption": 2.16,
            "procurement_cost_diesel": 300000.0,
        },
    ]

    battery_types = [
        {
            "name": "Ebusco 3.0 12 large battery",
            "procurement_cost": 190,
            "useful_life": 7,
            "cost_escalation": -0.03,
            "vehicle_type_id": 15,
        },
        {
            "name": "Solaris Urbino 18 large battery",
            "procurement_cost": 190,
            "useful_life": 7,
            "cost_escalation": -0.03,
            "vehicle_type_id": 16,
        },
        {
            "name": "Alexander Dennis Enviro500EV large battery",
            "procurement_cost": 190,
            "useful_life": 7,
            "cost_escalation": -0.03,
            "vehicle_type_id": 17,
        },
    ]

    charging_point_types = [
        {
            "type": "depot",
            "name": "Depot Charging Point",
            "procurement_cost": 119899.50,
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
        {
            "type": "opportunity",
            "name": "Opportunity Charging Point",
            "procurement_cost": 299748.74,
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
    ]

    charging_infrastructure = [
        {
            "type": "depot",
            "name": "Depot Charging Infrastructure",
            "procurement_cost": 2397989.95,  # TODO
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
        {
            "type": "station",
            "name": "Opportunity Charging Infrastructure",
            "procurement_cost": 269773.87,
            "useful_life": 20,
            "cost_escalation": 0.02,
        },
    ]

    scenario_tco_parameters = {
        "project_duration": 20,
        "interest_rate": 0.04,
        "inflation_rate": 0.02,
        "staff_cost": 25.0,  # calculated: 35,000 € p.a. per driver/1600 h p.a. per driver
        "fuel_cost": 1.5,  # diesel cost in EUR per litre
        "energy_cost": 0.1794,  # electricity cost in EUR per kWh
        "maint_cost": 0.35,  # Maintenance cost of electric buses in EUR per km
        "maint_cost_diesel": 0.45,  # Maintenance cost of diesel buses in EUR per km
        "maint_infr_cost": 1000,  # Maintenance cost infrastructure per year and charging slot
        "taxes": 278,  # Taxes and insurance cost in EUR per year and bus
        "insurance": 9693,  # DCO #9703, # EBU
        # Cost escalation factors (cef / pef)
        "pef_general": 0.02,
        "pef_wages": 0.025,
        "pef_energy": 0.038,
        "pef_fuel": 0.0,
        "pef_insurance": 0.02,
    }

    init_tco_parameters(
        scenario=SCENARIO_ID,
        database_url=DATABASE_URL,
        scenario_tco_parameters=scenario_tco_parameters,
        vehicle_types=vehicle_types,
        battery_types=battery_types,
        charging_point_types=charging_point_types,
        charging_infrastructure=charging_infrastructure,
    )

    tco_calculator = TCOCalculator(
        scenario=SCENARIO_ID,
        database_url=DATABASE_URL,
        energy_consumption_mode="constant",
    )

    tco_calculator.calculate()

    print(tco_calculator.tco_unit_distance)
    tco_calculator.visualize()

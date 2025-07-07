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
import functions as f
import get_data as gd
from analysis import plot_scenarios,sensitivity_analysis, plot_efficiency, plot_scenario_info
from init_database import init_database

# Environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
#DATABASE_URL = 'postgresql://julian:password@localhost/eflips_tco'
SCENARIO_ID = os.environ.get('SCENARIO_ID')
INPUT_FILE = os.environ.get('INPUT_FILE') # 'input_tco.csv' in this case
INCLUDE_DETAILED_ANALYSIS = os.environ.get('INCLUDE_DETAILED_ANALYSIS')

# unzstd --long=31 results_for_tco.sql.zst --stdout | psql eflips_tco um DB neu zu laden. Erst alle Tabellen außer spatial_ref_sys auswählen und löschen (mit entf)!


if __name__ == "__main__":

    #-----------read the input data from a .csv file-----------#
    with open(INPUT_FILE, newline="") as file:
        f.read_json(file)

    #----------import all required data from the database----------#
    engine = create_engine(DATABASE_URL, echo=False)
    with Session(engine) as session:

        # Only the scenario, which was chosen in the environmental variables is considered.
        scenario = session.query(Scenario).filter(Scenario.id == SCENARIO_ID).one()

        # initialize the database and write the tco parameters in the database.
        init_database(session, scenario)

        # Get the number of vehicles used in the simulation by vehicle type including the tco parameters.
        vehicle_dict = gd.get_vehicle_count_dict(session, scenario)

        # Get the number of charging infrastructure and slots by type. There are only depot or
        # terminal stop (opportunity) charging stations.
        charging_infrastructure_by_type =gd.get_charging_stations_and_slots_tco(session, scenario)

        # Get the total fuel / energy consumption in fuel unit (kWh) from the database.
        total_energy_consumption = gd.get_total_energy_consumption(session, scenario)

        # Get the fleet mileage by vehicle type.
        fleet_mileage_by_vehicle_type = gd.get_fleet_mileage_by_vehicle_type(session, scenario)

        # Get the driver hours
        driver_hours = gd.get_driver_hours(session, scenario)

        #Get the battery size by bus type including the tco parameters
        battery_dict = gd.get_battery_size_dict(session, scenario)

        passenger_mileage = gd.get_passenger_mileage(session, scenario)

        session.close()

    #----------calculate some additional parameters----------#

    # Calculate the total number of vehicles. This is needed in the OPEX calculation.
    total_number_vehicles = sum(x["number_of_assets"] for key,x in vehicle_dict.items())
    total_number_charging_slots = sum(x["number_of_assets"] for key,x in charging_infrastructure_by_type.items() if key in ["120 kw_Slot INFRASTRUCTURE", "300 kw_Slot INFRASTRUCTURE"])

    # Calculate the annual fleet mileage in km from the vehicle dictionary.
    annual_fleet_mileage = sum([data["annual_mileage"] for key,data in vehicle_dict.items()])

    # For the diesel scenario: calculate the fuel consumption based on the mileage:
    if total_energy_consumption < 10:
        number_12m_bus = vehicle_dict["Ebusco 3.0 12 large battery VEHICLE"]["number_of_assets"]
        diesel_consumption = (44.9/100 * number_12m_bus/total_number_vehicles # Fuel consumption of the 12m rigid bus
                              +58.9/100 * (total_number_vehicles-number_12m_bus)/total_number_vehicles) # fuel consumption of 18m and double decker buses.
        total_energy_consumption = annual_fleet_mileage*diesel_consumption

    # Calculate the actual driver hours including a buffer.
    total_driver_hours = f.calculate_total_driver_hours(driver_hours)

    # make a dictionary including all tco parameters needed for the calculation
    capex_input_dict = vehicle_dict | battery_dict | charging_infrastructure_by_type
    #print(capex_input_dict)
    # Create a dictionary including all relevant OPEX parameters
    opex_input_dict = {
        "staff_cost": {
            "cost": p.staff_cost,
            "depending_on_scale": total_driver_hours,
            "cost_escalation": p.cef_wages
        },
        "maint_cost_vehicles": {
            "cost": p.maint_cost,
            "depending_on_scale": annual_fleet_mileage,
            "cost_escalation": p.cef_general
        },
        "maint_cost_infra":{
            "cost": p.maint_infr_cost,
            "depending_on_scale": total_number_charging_slots,
            "cost_escalation": p.cef_general
        },
        "fuel_cost": {
            "cost": p.fuel_cost,
            "depending_on_scale": total_energy_consumption,
            "cost_escalation": p.cef_fuel
        },
        "insurance": {
            "cost": p.insurance,
            "depending_on_scale": total_number_vehicles,
            "cost_escalation": p.cef_insurance
        },
        "taxes": {
            "cost": p.taxes,
            "depending_on_scale": total_number_vehicles,
            "cost_escalation": p.cef_general
        }
    }
    tco_input_dict = {
        "project_duration": p.project_duration,
        "interest_rate": p.interest_rate,
        "discount_rate": p.discount_rate,
        "scenario": SCENARIO_ID,
        "passenger_mileage": passenger_mileage,
        "annual_fleet_mileage": annual_fleet_mileage
    }

    # Calculate the TCO
    tco_result = f.tco_calculation(capex_input_dict,opex_input_dict,tco_input_dict, True)

    # TCO over project duration
    tco_pd = tco_result["TCO_over_PD"]

    # Annual TCO
    tco_ann =tco_pd / p.project_duration

    # Specific TCO over project duration
    tco_sp_pd = tco_pd/(annual_fleet_mileage*p.project_duration)

    # Print the results on the console if wanted.
    # print('The total cost of ownership over the project duration'
    #       ' of {} years is {:.2f} EUR.'.format(p.project_duration, tco_pd))
    # print('Annual total cost of ownership over the project duration'
    #       ' of {} years is {:.2f} EUR per year.'.format(p.project_duration, tco_ann))
    # print('The specific total cost of ownership over the project duration'
    #       ' of {} years is {:.2f} EUR per km.'.format(p.project_duration, round(tco_sp_pd,2)))
    # print('The annual fleet mileage is {:.2f} km with a total of {} buses and an average energy '
    #       'consumption of {} kWh/km.'.format(annual_fleet_mileage, (total_number_vehicles),
    #                                          (round(total_energy_consumption / annual_fleet_mileage,2))))

    # Plot the specific TCO and save the plot to the repository.
    f.tco_plot(tco_result, SCENARIO_ID)

    #-----------Save the output to a JSON file-----------#

    # Calculate the total nuber of charging slots.
    total_number_charging_slots = {
        "120 kw_Slot": charging_infrastructure_by_type.get("120 kw_Slot INFRASTRUCTURE", {}).get("number_of_assets",0),
        "300 kw_Slot": charging_infrastructure_by_type.get("300 kw_Slot INFRASTRUCTURE",{}).get("number_of_assets",0),
        "Total": (charging_infrastructure_by_type.get("120 kw_Slot INFRASTRUCTURE", {}).get("number_of_assets",0)
                  + charging_infrastructure_by_type.get("300 kw_Slot INFRASTRUCTURE", {}).get("number_of_assets",0))
    }

    total_charging_stations = {
        "DEPOT Station:": charging_infrastructure_by_type.get("DEPOT Station INFRASTRUCTURE", {}).get("number_of_assets",0),
        "OPPORTUNITY Station": charging_infrastructure_by_type.get("OPPORTUNITY Station INFRASTRUCTURE", {}).get("number_of_assets",0),
        "Total": (charging_infrastructure_by_type.get("DEPOT Station INFRASTRUCTURE",{}).get("number_of_assets",0)
                  + charging_infrastructure_by_type.get("OPPORTUNITY Station INFRASTRUCTURE", {}).get("number_of_assets",0))
    }

    # The dictionary which will be saved to the json file is created.
    data_out = {
        "input_data" : capex_input_dict | {
            "Discount_rate": ((p.discount_rate*100), "% p.a."),
            "Interest_rate": ((p.interest_rate*100), "% p.a."),
            "Project_duration": (p.project_duration, "years"),
            "Staff_cost": (p.staff_cost, "EUR/h"),
            "Fuel_cost": (p.fuel_cost,"EUR/kWh"),
            "Maintenance_cost_vehicles": (p.maint_cost,"EUR/km"),
            "Maintenance_cost_infrastructure": (p.maint_infr_cost,"EUR/slot"),
            "Taxes": (p.taxes,"EUR/Bus p.a."),
            "Insurance": (p.insurance,"EUR/Bus p.a."),
            "General_cost_escalation": ((p.cef_general*100), "% p.a."),
            "Wages_cost_escalation": ((p.cef_wages*100), "% p.a."),
            "Fuel_cost_escalation": ((p.cef_fuel*100), "% p.a."),
            "Insurance_cost_escalation":((p.cef_insurance*100),"% p.a."),
            "Vehicle_cost_escalation":((p.cef_vehicles*100),"% p.a."),
            "Battery_cost_escalation": ((p.cef_battery*100),"% p.a."),
            "Infrastructure_cost_escalation": ((p.cef_infra*100),"% p.a.")
        },
        "Results":{
            "Number_of_vehicles": total_number_vehicles,
            "Number of charging slots": total_number_charging_slots,
            "Number of charging stations": total_charging_stations,
            "Total_annual_driver_hours": (round(total_driver_hours, 2), "h p.a."),
            "Total_annual_fleet_mileage": (round(annual_fleet_mileage,2), "km p.a."),
            "Total_annual_passenger_mileage": (round(passenger_mileage,2), "km p.a."),
            "Average_energy_consumption": (round(total_energy_consumption / annual_fleet_mileage,2), "kWh/km"),
            "Total_energy_consumption": (round(total_energy_consumption/1000,2), 'MWh'),
            "Total_TCO_over_pd": (round(tco_result["TCO_over_PD"], 2), "EUR"),
            "Annual_TCO": (round(tco_result["Annual_TCO"], 2), "EUR p.a."),
            "Specific_TCO": (round(tco_result["Specific_TCO_over_PD"], 2), "EUR/km")
        }
    }

    # Save the data in the json file.
    with open('results_scn_{}.json'.format(SCENARIO_ID), 'w') as out_file:
        json.dump(data_out, out_file, indent=4)
        print("\nThe TCO calculation has been completed successfully. The results are saved in 'results_scn_{}.json'.\n"
              "Before recalculating the TCO, make sure to save your results in a different file as 'results_scn_{}.json' will be overwritten.".format(SCENARIO_ID, SCENARIO_ID))

    if INCLUDE_DETAILED_ANALYSIS == 'True':
        plot_scenarios([1, 3, 4])
        plot_efficiency([1,3,4])
        plot_scenario_info([1,3,4])
        sensitivity_analysis(capex_input_dict, opex_input_dict, tco_input_dict,
                            ["procurement", "useful_life", "staff_cost", "maint_cost_vehicles",
                             "maint_cost_infra", "fuel_cost", "interest_rate", "discount_rate"], SCENARIO_ID)

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
from init_database import init_database

# Environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
#DATABASE_URL = 'postgresql://julian:password@localhost/eflips_tco'
SCENARIO_ID = os.environ.get('SCENARIO_ID')
INPUT_FILE = os.environ.get('INPUT_FILE') # 'input_tco.csv' in this case

# unzstd --long=31 results_for_tco.sql.zst --stdout | psql eflips_tco um DB neu zu laden. Erst alle Tabellen außer spatial_ref_sys auswählen und löschen (mit entf)!


if __name__ == "__main__":

    #-----------read the input data from a .csv file-----------#
    with open(INPUT_FILE, newline="") as csvfile:
        f.read_csv(csvfile)

    #----------import all required data from the database----------#
    engine = create_engine(DATABASE_URL, echo=False)
    with Session(engine) as session:

        # Only the scenario, which was chosen in the environmental varibales is considered.
        scenario = session.query(Scenario).filter(Scenario.id == SCENARIO_ID).first()

        init_database(session, scenario)

        # Get the number of vehicles used in the simulation by vehicle type including the tco parameters.
        vehicles_tco = gd.get_vehicle_count_by_type_tco_parameters(session, scenario)

        # Get the number of charging infrastructure and slots by type. There are only depot or
        # terminal stop (opportunity) charging stations.
        charging_infrastructure_by_type =gd.get_charging_stations_and_slots_tco(session, scenario)

        # Get the total fuel / energy consumption in fuel unit (kWh) from the database.
        total_energy_consumption = gd.get_total_energy_consumption(session, scenario)

        # Get the fleet mileage by vehicle type.
        fleet_mileage_by_vehicle_type = gd.get_fleet_mileage_by_vehicle_type(session, scenario)

        # Get the annual fleet mileage in km.
        annual_fleet_mileage = gd.get_total_fleet_mileage(session, scenario)

        # Get the driver hours
        total_driver_hours = gd.get_driver_hours(session, scenario)

        #Get the battery size by bus type including the tco parameters
        battery_size_by_vehicle_type_tco = gd.get_battery_size_tco(session, scenario)

        session.close()


    # ----------calculate some additional parameters----------#

    # Calculate the total number of vehicles. This is needed in the OPEX calculation.
    total_number_vehicles = sum(x[2] for x in vehicles_tco)

    # Some parameters are put into lists to make the calculations easier
    opex_price_list = [p.staff_cost, p.maint_cost, p.fuel_cost, p.insurance, p.taxes]
    opex_amount_list = [total_driver_hours, annual_fleet_mileage, total_energy_consumption, total_number_vehicles, total_number_vehicles]
    opex_pefs_list = [p.pef_wages, p.pef_general, p.pef_fuel, p.pef_general, p.pef_general]


    #----------TCO calculation----------#

    # ----------Total CAPEX----------#

    # The CAPEX of the vehicles, the batteries and the infrastructure is calculated using the total_proc_cef method
    # in order to obtain the CAPEX part of the TCO.
    Total_CAPEX = 0

    # Vehicles
    for vehicle in vehicles_tco:
        procurement_per_vehicle_type = f.total_proc_cef(vehicle[3].get("procurement_cost"), vehicle[3].get("useful_life"),
                                                        p.project_duration, vehicle[3].get("cost_escalation"),
                                                        p.interest_rate, p.inflation_rate)
        Total_CAPEX += procurement_per_vehicle_type * vehicle[2]

    # Batteries
    for battery in battery_size_by_vehicle_type_tco:
        procurement_per_battery = number_batteries = 0
        # To determine the number of batteries and the overall procurement cost, the respective vehicle number is
        # matched with the respective battery based on the vehicle name.
        for vehicle in vehicles_tco:
            if battery[1] == vehicle[1]:
                procurement_per_battery = battery[2] * battery[3].get("procurement_cost")
                number_batteries = vehicle[2]
                break
        procurement_per_battery_type = f.total_proc_cef(procurement_per_battery, battery[3].get("useful_life"), p.project_duration,
                                                        battery[3].get("cost_escalation"), p.interest_rate, p.inflation_rate)
        Total_CAPEX += procurement_per_battery_type * number_batteries

    # Charging infrastructure
    for key,char_infra in charging_infrastructure_by_type.items():
        # Calculate the procurement cost for each charging infrastructure type.
        procurement_per_char_infra_type = f.total_proc_cef(
            char_infra["tco_parameters"].get("procurement_cost"), char_infra["tco_parameters"].get("useful_life"),
            p.project_duration, char_infra["tco_parameters"].get("cost_escalation"), p.interest_rate, p.inflation_rate)
        Total_CAPEX += procurement_per_char_infra_type * char_infra["number_of_type"]

    #----------Total OPEX----------#

    Total_OPEX = 0

    # Calculate the OPEX over the whole project duration
    for i in range(p.project_duration):
        total_opex_in_respective_year = 0

        # Calculate all OPEX
        for j in range(len(opex_price_list)):
            total_opex_in_respective_year += f.future_cost(opex_pefs_list[j], opex_price_list[j], i)[0] * opex_amount_list[j]
        Total_OPEX += f.net_present_value(total_opex_in_respective_year, i, p.inflation_rate)[0]

    #----------Calculation of three kinds of TCO----------#

    # TCO over project duration
    tco_pd = Total_CAPEX + Total_OPEX

    # Annual TCO
    tco_ann =tco_pd / p.project_duration

    # Specific TCO over project duration
    tco_sp_pd = tco_pd/(annual_fleet_mileage*p.project_duration)

    # Print the results on the console if wanted.
    print('The total cost of ownership over the project duration'
          ' of {} years is {:.2f} EUR.'.format(p.project_duration, tco_pd))
    print('Annual total cost of ownership over the project duration'
          ' of {} years is {:.2f} EUR per year.'.format(p.project_duration, tco_ann))
    print('The specific total cost of ownership over the project duration'
          ' of {} years is {:.2f} EUR per km.'.format(p.project_duration, tco_sp_pd))
    print('The annual fleet mileage is {:.2f} km with a total of {} buses and an average energy '
          'consumption of {} kWh/km.'.format(annual_fleet_mileage, (total_number_vehicles),
                                                 (round(total_energy_consumption / annual_fleet_mileage,2))))

    #-----------Save the output to a JSON file-----------#
    vehicle_input = []
    battery_input = []
    infra_input = []
    keys = ["name", "procurement_cost", "useful_life", "cost_escalation"]
    for i in p.Vehicles:
        vehicle_in={}
        for j in range(len(keys)):
            vehicle_in[keys[j]] = i[j]
        vehicle_input.append(vehicle_in)
    for i in p.Battery:
        battery_in = {}
        for j in range(len(keys)):
            battery_in[keys[j]] = i[j]
        battery_input.append(battery_in)
    for i in p.Charging_Stations:
        infra_in = {}
        for j in range(len(keys)):
            infra_in[keys[j]] = i[j]
        infra_input.append(infra_in)

    # Calculate the total nuber of charging slots.
    total_number_charging_slots = {
        "120 kw_Slot": charging_infrastructure_by_type["120 kw_Slot"]["number_of_type"],
        "300 kw_Slot": charging_infrastructure_by_type["300 kw_Slot"]["number_of_type"],
        "Total": (charging_infrastructure_by_type["120 kw_Slot"]["number_of_type"]
                  + charging_infrastructure_by_type["300 kw_Slot"]["number_of_type"])
    }

    # The dictionary which will be saved to the json file is created.
    data_out = {
        "input_data" : {
            "Vehicles": vehicle_input,
            "Battery": battery_input,
            "Charging_Stations": infra_input,
            "Discount_rate": (p.inflation_rate, "% p.a."),
            "Interest_rate": (p.inflation_rate, "% p.a."),
            "Project_duration": (p.project_duration, "years"),
            "Staff_cost": (p.staff_cost, "EUR/h"),
            "Fuel_cost": (p.fuel_cost,"EUR/kWh"),
            "Maintenance_cost_vehicles": (p.maint_cost,"EUR/km"),
            "Maintenance_cost_infrastructure": (p.maint_infr_cost,"EUR/slot"),
            "Taxes": (p.taxes,"EUR/Bus p.a."),
            "Insurance": (p.insurance,"EUR/Bus p.a."),
            "General_cost_escalation": (p.pef_general, "% p.a."),
            "Wages_cost_escalation": (p.pef_wages, "% p.a."),
            "Fuel_cost_escalation": (p.fuel_cost, "% p.a.")
        },
        "Results":{
            "Number_of_vehicles": total_number_vehicles,
            "Number of charging slots": total_number_charging_slots,
            "Total_annual_driver_hours": (total_driver_hours, "h p.a."),
            "Total_annual_fleet_mileage": (annual_fleet_mileage, "km p.a."),
            "Total_TCO_over_pd": (round(tco_pd, 2), "EUR"),
            "Annual_TCO": (round(tco_ann, 2), "EUR p.a."),
            "Specific_TCO": (round(tco_sp_pd, 2), "EUR/km")
        }
    }

    # Save the data in the json file.
    with open('results.json', 'w') as outfile:
        json.dump(data_out, outfile, indent=4)
        print("\nThe TCO calculation has been completed successfully. The results are saved in 'results.json'.\n"
              "Before recalculating the TCO, make sure to save your results in a different file as 'results.json' will be overwritten.")

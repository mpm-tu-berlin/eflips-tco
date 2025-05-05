#!/usr/bin/env python3

"""
This is the main module of the project. It should contain the main entry point of the project. By
running this, the essential functionality of the project should be executed.
"""
#from numpy.lib.tests.test_format import endian
from sqlalchemy.orm import Session
from eflips.model import Scenario
from sqlalchemy import create_engine#, func

import os
import json

import parameters as p
import functions as f
import get_data as gd

# Environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
#DATABASE_URL = 'postgresql://julian:password@localhost/eflips_tco'
SCENARIO_ID = os.environ.get('SCENARIO_ID')
INPUT_FILE = os.environ.get('INPUT_FILE') # 'input_tco.csv' in this case

if __name__ == "__main__":

    engine = create_engine(DATABASE_URL, echo=False)
    with Session(engine) as session:

        """Every scenario is calculated"""
        scenario = session.query(Scenario).filter(Scenario.id == SCENARIO_ID).scalar()

        """ Calculating the number of vehicles used in the simulation by vehicle type."""
        vehicle_count_by_type = gd.get_vehicle_count_by_type(session, scenario)

        """Calculate the number of charging infrastructure and slots by type. There are only depot or terminal stop (opportunity) charging stations"""
        charging_stations_by_type =gd.get_charging_stations_and_slots_count(session, scenario)

        " Get the total fuel (Energy) consumption from the database"
        total_energy_consumption = gd.get_total_energy_consumption(session, scenario)

        """ Get the fleet mileage by vehicle type """
        fleet_mileage_by_vehicle_type = gd.get_fleet_mileage_by_vehicle_type(session, scenario)

        """Get the total fleet mileage"""
        total_fleet_mileage = gd.get_total_fleet_mileage(session, scenario)

        """Get the driver hours"""
        total_driver_hours = gd.get_driver_hours(session, scenario)

        """Get the battery size by bus type"""
        battery_size = gd.get_battery_size(session, scenario)

        session.close()

    # List with the number of charging infrastructure by type which should be replaced by a "get_data" function,
    # which counts the charging infrastructure.
    # This should be removed, if the database includes charging infrastructure
    charging_stations_by_type = [
        (SCENARIO_ID, "OPPORTUNITY Station", 3),# OPPORTUNITY charging station
        (SCENARIO_ID, "OPPORTUNITY Slot", 15),  # OPPORTUNITY charging slot
        (SCENARIO_ID, "DEPOT Station", 1), # DEPOT charging station
        (SCENARIO_ID, "DEPOT Slot",8)  # DEPOT charging slot
    ]

    #-----------read the input data from a .csv file-----------#
    with open(INPUT_FILE, newline="") as csvfile:
        f.read_csv(csvfile)


    """ 
    Parameters that can be determined from the eFlips database 
    """

    # In order to calculate the TCO, a list with tuples is created. The tuples contain the name, the number, the
    # procurement cost, the useful life and the cost escalation. This is done using the make_parameter_list method.
    vehicles = f.make_parameter_list(vehicle_count_by_type, p.Vehicles)
    battery_by_vehicle= f.make_parameter_list(battery_size, p.Battery)
    charging_infrastructure_by_type = f.make_parameter_list(charging_stations_by_type, p.Charging_Stations)

    # Calculate the total number of vehicles. This is needed in the OPEX calculation.
    total_number_vehicles = sum(x[1] for x in vehicles)

    # Energy / Fuel consumption in fuel unit
    fuel_consumption = total_energy_consumption[1]

    # Annual fleet mileage in km
    fleet_mileage = total_fleet_mileage[1]

    # driver hours
    driver_hours = total_driver_hours[1]

    # Some parameters are put into lists to make the calculations easier
    opex_price_list = [p.staff_cost, p.maint_cost, p.fuel_cost, p.insurance, p.taxes]
    opex_amount_list = [driver_hours, fleet_mileage, fuel_consumption, total_number_vehicles, total_number_vehicles]
    opex_pefs_list = [p.pef_wages, p.pef_general, p.pef_fuel, p.pef_general, p.pef_general]

    """ 
    TCO calculation
    """
    """ Total CAPEX """

    # The CAPEX of the vehicles, the batteries and the infrastructure is calculated using the total_proc_cef method
    # in order to obtain the CAPEX part of the TCO.
    Total_CAPEX = 0
    # Vehicles
    for vehicle in vehicles:
        procurement_per_vehicle_type = f.total_proc_cef(vehicle[2], vehicle[3], p.project_duration, vehicle[4],
                                                        p.interest_rate, p.inflation_rate)
        Total_CAPEX += procurement_per_vehicle_type * vehicle[1]
    # Batteries
    for battery in battery_by_vehicle:
        procurement_per_battery = number_batteries = 0
        # To determine the number of batteries and the overall procurement cost, the respective vehicle number is
        # matched with the respective battery based on the vehicle name.
        for vehicle in vehicles:
            if battery[0] == vehicle[0]:
                procurement_per_battery = battery[1] * battery[2]
                number_batteries = vehicle[1]
        procurement_per_battery_type = f.total_proc_cef(procurement_per_battery, battery[3], p.project_duration,
                                                        battery[4], p.interest_rate, p.inflation_rate)
        Total_CAPEX += procurement_per_battery_type * number_batteries
    # Charging infrastructure
    for char_infra in charging_infrastructure_by_type:
        procurement_per_char_infra_type = f.total_proc_cef(char_infra[2], char_infra[3], p.project_duration,
                                                               char_infra[4], p.interest_rate, p.inflation_rate)
        Total_CAPEX += procurement_per_char_infra_type * char_infra[1]

    """ Total OPEX """

    Total_OPEX = 0
    for i in range(p.project_duration):
        total_opex_in_respective_year = 0
        for j in range(len(opex_price_list)):
            total_opex_in_respective_year += f.future_cost(opex_pefs_list[j], opex_price_list[j], i)[0] * opex_amount_list[j]
        Total_OPEX += f.net_present_value(total_opex_in_respective_year, i, p.inflation_rate)[0]

    """ Calculate three kinds of TCO """

    # TCO over project duration
    tco_pd = Total_CAPEX + Total_OPEX

    # Annual TCO
    tco_ann =tco_pd / p.project_duration

    # Specific TCO over project duration
    tco_sp_pd = tco_pd/(fleet_mileage*p.project_duration)

    # Print the results on the console if wanted.
    #print('The total cost of ownership over the project duration'
    #      ' of {} years is {:.2f} EUR.'.format(p.project_duration, tco_pd))
    #print('Annual total cost of ownership over the project duration'
    #      ' of {} years is {:.2f} EUR per year.'.format(p.project_duration, tco_ann))
    #print('The specific total cost of ownership over the project duration'
    #      ' of {} years is {:.2f} EUR per km.'.format(p.project_duration, tco_sp_pd))
    #print('The annual fleet mileage is {:.2f} km with a total of {} buses and an average energy '
    #      'consumption of {} kWh/km.'.format(fleet_mileage, (total_number_vehicles),
    #                                             (round(total_energy_consumption[1] / total_fleet_mileage[1],2))))

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
            "Number_of_buses": total_number_vehicles,
            "Total_annual_driver_hours": (driver_hours, "h p.a."),
            "Total_annual_fleet_mileage": (fleet_mileage, "km p.a."),
            "Total_TCO_over_pd": (round(tco_pd, 2), "EUR"),
            "Annual_TCO": (round(tco_ann, 2), "EUR p.a."),
            "Specific_TCO": (round(tco_sp_pd, 2), "EUR/km")
        }
    }

    # Save the data in the json file.
    with open('results.json', 'w') as outfile:
        json.dump(data_out, outfile, indent=4)
        print("The TCO calculation has been completed successfully. The results are saved in 'results.json'.\n"
              "Before recalculating the TCO, make sure to save your results in a different file as 'results.json' will be overwritten.")
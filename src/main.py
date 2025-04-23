#!/usr/bin/env python3

"""
This is the main module of the project. It should contain the main entry point of the project. By
running this, the essential functionality of the project should be executed.
"""
from numpy.lib.tests.test_format import endian
from sqlalchemy.orm import Session
from eflips.model import Scenario
from sqlalchemy import create_engine, func

import os

import functions
import get_data
import parameters as p
import functions as f
import get_data as gd

DATABASE_URL = os.environ.get('DATABASE_URL')
#DATABASE_URL = 'postgresql://julian:password@localhost/eflips_tco'

SCENARIO_ID = os.environ.get('SCENARIO_ID')

if __name__ == "__main__":

    engine = create_engine(DATABASE_URL, echo=False)
    with Session(engine) as session:

        """Every scenario is calculated"""
        scenario = session.query(Scenario).filter(Scenario.id == SCENARIO_ID).scalar()

        """ Calculating the number of vehicles used in the simulation by vehicle type."""
        vehicle_count_by_type = gd.get_vehicle_count_by_type(session, scenario)

        """Calculate the number of charging infrastructure and slots by type. There are only depot or terminal stop (opportunity) charging stations"""
        charging_infra_count_by_type =gd.get_charging_stations_and_slots_count(session, scenario)

        " Get the total fuel (Energy) consumption from the database"
        total_energy_consumption = gd.get_total_energy_consumption(session, scenario)

        """ Get the fleet mileage by vehicle type """
        fleet_mileage_by_vehicle_type = gd.get_fleet_mileage_by_vehicle_type(session, scenario)

        """Get the total fleet mileage"""
        total_fleet_mileage = gd.total_fleet_mileage(session, scenario)

        """Get the driver hours"""
        total_driver_hours = gd.get_driver_hours(session, scenario)

        """Get the battery size by bus type"""
        battery_size = gd.get_battery_size(session, scenario)

        session.close()

    """ 
    Parameters that can be determined from the eFlips database 
    """

    """ Number of buses used in the simulation """
    num_12m_beb = vehicle_count_by_type[0][2]
    num_18m_beb = vehicle_count_by_type[1][2]

    """ Procurement cost of the batteries"""
    proc_batt_12m_beb = battery_size[0][0]*p.proc_battery
    proc_batt_18m_beb = battery_size[1][0] * p.proc_battery
    print(proc_batt_12m_beb, proc_batt_18m_beb)
    """ Number of charging slots and stations used in the simulation (depot charging [dc] and terminal stop charging [tsc])"""
    num_dc_stations = 1
    num_dc_slots = 8
    num_tsc_stations = 3
    num_tsc_slots = 15

    """ Energy / Fuel consumption in fuel unit"""
    fuel_consumption = total_energy_consumption[1]

    """ Annual fleet mileage in km """
    fleet_mileage = total_fleet_mileage[1]

    """ driver hours """
    driver_hours = total_driver_hours[1]

    """ Some parameters are put into lists to make the calculations easier"""
    proc_list = [p.proc_12m_beb, proc_batt_12m_beb, p.proc_18m_beb, proc_batt_18m_beb, p.proc_dc_station, p.proc_dc_slot, p.proc_tsc_station, p.proc_tsc_slot]
    uf_list = [p.uf_12m_beb, p.uf_battery, p.uf_18m_beb, p.uf_battery, p.uf_dc_station, p.uf_dc_slot, p.uf_tsc_station, p.uf_tsc_slot]
    num_list = [num_12m_beb, num_12m_beb, num_18m_beb, num_18m_beb, num_dc_stations, num_dc_slots, num_tsc_stations, num_tsc_slots]
    capex_cef_list = [p.cef_vehicle, p.cef_vehicle, p.cef_vehicle, p.pef_battery, p.pef_general, p.pef_general, p.pef_general, p.pef_general]

    opex_price_list = [p.staff_cost, p.maint_cost, p.fuel_cost, p.insurance, p.taxes]
    opex_amount_list = [driver_hours, fleet_mileage, fuel_consumption, (num_18m_beb+num_12m_beb), (num_18m_beb+num_12m_beb)]
    opex_pefs_list = [p.pef_wages, p.pef_general, p.pef_wages, p.pef_general, p.pef_general]

    """ 
    TCO calculation
    """

    """ Total CAPEX """
    #total_proc_12m_beb = functions.total_proc_cef(p.proc_12m_beb, p.uf_12m_beb, p.project_duration, p.pef_general, p.interest_rate, p.inflation_rate)
    Total_CAPEX = 0
    for i in range(len(proc_list)):
        total_procurement_cost_per_asset = f.total_proc_cef(proc_list[i], uf_list[i], p.project_duration, capex_cef_list[i], p.interest_rate, p.inflation_rate)
        Total_CAPEX += total_procurement_cost_per_asset * num_list[i]

    """ Total OPEX """

    Total_OPEX = 0
    for i in range(p.project_duration):
        total_opex_in_respective_year = 0
        for j in range(len(opex_price_list)):
            total_opex_in_respective_year += f.future_cost(opex_pefs_list[j], opex_price_list[j], i)[0] * opex_amount_list[j]
        Total_OPEX += f.net_present_value(total_opex_in_respective_year, i, p.inflation_rate)[0]
    """ Calculate three kinds of TCO """

    """ TCO over project duration """
    tco_pd = Total_CAPEX + Total_OPEX

    """ Annual TCO  """
    ann_tco =tco_pd / p.project_duration

    """ specific TCO over project duration """
    sp_tco_pd = tco_pd/(fleet_mileage*p.project_duration)

    """ Print the results on the console. """
    print('The total cost of ownership over the project duration'
          ' of {} years is {:.2f} EUR.'.format(p.project_duration, tco_pd))
    print('Annual total cost of ownership over the project duration'
          ' of {} years is {:.2f} EUR per year.'.format(p.project_duration, ann_tco))
    print('The specific total cost of ownership over the project duration'
          ' of {} years is {:.2f} EUR per km.'.format(p.project_duration, sp_tco_pd))
    print('The annual fleet mileage is {:.2f} km with a total of {} buses and an average energy consumption of {:.2f} kWh/km.'.format(fleet_mileage, (num_18m_beb+num_12m_beb), (total_energy_consumption[1] / total_fleet_mileage[1])))

    """ " Annuity of a single bus is calculated "
    ann=annuity(proc_12m_beb, project_duration, interest_rate)
    for i in range(project_duration):
        print(net_present_value(ann, i))

    "Total procurement cost of a single bus is calculated."
    t_p_c = total_proc(proc_12m_beb, project_duration, interest_rate, inflation_rate)
    print("Total procurement cost of a single 12m bus adjusted for inflation:",t_p_c)

    t_p_c_npv = 0
    for i in range(project_duration):
        t_p_c_npv += net_present_value(ann, i, inflation_rate)[0]
    print("Total procurement cost of a single 12m bus adjusted for inflation:", t_p_c_npv)"""

    """
        print(vehicle_count_by_type)
        print(charging_infra_count_by_type)
        print(total_energy_consumption)
        print(fleet_mileage_by_vehicle_type)
        print(total_fleet_mileage)
        print(total_driver_hours)
        print("Simulation period:", get_data.get_simulation_period(session, scenario))
    """
    # Input und Output in eine csv Datei speichern:
    #Daten = ["procurement_12_m_bus", "procurement_18_m_bus", "procurement_double_decker_bus", "useful_life_12m_bus", "useful_life_18m_bus", "useful_life_decker_bus", "useful_life_double_decker_bus"]

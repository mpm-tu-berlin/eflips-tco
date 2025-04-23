import datetime
from typing import List, Tuple, Any
from eflips.model import Vehicle, Station, Event, VehicleType, Route, Trip
from sqlalchemy import or_
from sqlalchemy import func
import numpy as np

import functions

""" Calculating the number of vehicles per vehicle type."""
def get_vehicle_count_by_type(session, scenario):
    # Gets the vehicle types used in the current scenario
    vehicle_types = scenario.vehicle_types
    """ Create empty list in which the number and type of buses are listed."""
    vehicle_number_by_type: list[tuple[int, str, int]] = []
    for vt in vehicle_types:
        """Counts all vehicles and saves them in the list including Scenario.id and VehicleType.name"""
        vt_count = session.query(
            Vehicle
        ).filter(
            Vehicle.scenario == scenario
        ).filter(
            Vehicle.vehicle_type_id == vt.id
        ).count()
        vehicle_number_by_type.append((scenario.id, vt.name, vt_count))
    return vehicle_number_by_type

### This function should be replaced by the "power_and_output" function from eFlips-eval, output
"""Calculate the number of charging infrastructure and slots by type."""
def get_charging_stations_and_slots_count(session, scenario):
    #There are only depot or terminal stop (opportunity) charging stations
    charging_types = ["DEPOT", "OPPORTUNITY"]
    # Counting the charging stations and the charging slots for both types
    charging_infra_by_type: list[tuple[int, str, int, int]] = []
    for ct in charging_types:
        # Counts charging stations by type
        cs_count = session.query(
            Station
        ).filter(
            Station.scenario_id == scenario.id
        ).filter(
            Station.charge_type == ct
        ).count()
        # Counts charging slots by station type
        cslots = session.query(
            Station
        ).filter(
            Station.scenario_id == scenario.id
        ).filter(
            Station.charge_type == ct
        ).all()
        # Counting the total slots by summing the amount_charging_places attribute
        cslots_count = 0
        for cs in cslots:
            cslots_count += cs.amount_charging_places
        charging_infra_by_type.append((scenario.id, ct, cs_count, cslots_count))
    return charging_infra_by_type

""" Get the total fuel (Energy) consumption from the database. As the scenario only simulates a time period 
of 7 days, the energy consumption must be multiplied. """
def get_total_energy_consumption(session, scenario):
    # obtain the energy consumption as the difference in state of charge before and after the charging events
    result = session.query(
        func.sum(Event.soc_start - Event.soc_end),
        VehicleType.battery_capacity
    ).select_from(
        Event
    ).join(
        VehicleType, Event.vehicle_type_id == VehicleType.id
    ).filter(
        Event.event_type != 'CHARGING_DEPOT'
    ).filter(
        Event.scenario_id == scenario.id
    ).group_by(VehicleType.battery_capacity).all()
    # Calculate the annual energy consumption
    energy_consumption = sum(t[0]*t[1] for t in result)*functions.sim_period_to_year(session = session, scenario = scenario)
    return (scenario.id, energy_consumption)

"""Get the fleet mileage by vehicle type """
def get_fleet_mileage_by_vehicle_type(session, scenario):
    result = session.query(
        scenario.id,
        VehicleType.name,
        func.sum(Route.distance)
    ).join(
        Trip, Route.id == Trip.route_id
    ).join(
        Event, Event.trip_id == Trip.id
    ).join(
        VehicleType, Event.vehicle_type_id == VehicleType.id
    ).filter(
        Event.scenario_id == scenario.id
    ).group_by(VehicleType.name).all()
    #The total mileage by vehicle_type over one year is calculated
    annual_mileage_by_vtype: list[tuple[int, str, float]] = []
    for i in range(len(result)):
        # the respective tuple is added to the list
        annual_mileage_by_vtype.append((result[i][0], result[i][1], result[i][2]*functions.sim_period_to_year(session, scenario)/1000))
    return annual_mileage_by_vtype

""" Calculates the total fleet mileage not grouped by vehicle type"""
def total_fleet_mileage(session, scenario):
    mileage_by_vtype = get_fleet_mileage_by_vehicle_type(session, scenario)
    # Next, the total fleet mileage over the simulation period is calculated
    total_mileage = sum([t[2] for t in mileage_by_vtype])
    return (scenario.id, total_mileage)

""" Calculate the driver hours  """
def get_driver_hours(session, scenario):
    result = session.query(
        func.sum(Event.time_end - Event.time_start)
    ).filter(
        Event.scenario_id == scenario.id
    ).filter(
        or_(Event.event_type == 'DRIVING', Event.event_type == 'DRIVING')
    ).one()
    # Annual driver hours are calculated
    driver_hours = functions.sim_period_to_year(session = session, scenario = scenario)* result[0].total_seconds() / 3600
    return(scenario.id, driver_hours)


""" This method returns the simulation duration using the earliest and latest Event. 
It is used by the functions.sim_period_to_year() function."""
def get_simulation_period(session, scenario):
    result = session.query(
        func.min(Event.time_start),
        func.max(Event.time_end)
    ).filter(
    Event.scenario_id == scenario.id
    ).one()
    return result[1]-result[0]

""" This is a method, which returns the battery size by vehicle type. """
def get_battery_size(session, scenario):
    result = session.query(
        VehicleType.battery_capacity,
        VehicleType.name
    ).filter(
        VehicleType.scenario_id == scenario.id
    ).all()
    return result
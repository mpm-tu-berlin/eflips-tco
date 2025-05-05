import datetime
from typing import List, Tuple, Any
from eflips.model import Vehicle, Station, Event, VehicleType, Route, Trip
from sqlalchemy import or_
from sqlalchemy import func
import numpy as np
import functions


""" Calculating the number of vehicles per vehicle type."""
def get_vehicle_count_by_type(session, scenario):
    """
    This method gets the number of vehicles sorted by the vehicle type from the session provided.
    :param session: A session object.
    :param scenario: A scenario object.
    :return: A list of tuples including the scenario id of the calculated scenario, the name of the vehicle type and the number of vehicles of the respective vehicle type.
    """
    # Gets the vehicle types used in the current scenario
    vehicle_types = scenario.vehicle_types
    """ Create empty list in which the number and type of buses are listed."""
    vehicle_number_by_type: list[tuple[int, str, int]] = []
    for vt in vehicle_types:
        """Counts all vehicles and saves them in the list including Scenario.id and VehicleType.name"""
        vt_count = session.query(
            Vehicle
        ).filter(
            Vehicle.scenario == scenario,
            Vehicle.vehicle_type_id == vt.id
        ).count()
        vehicle_number_by_type.append((scenario.id, vt.name, vt_count))
    return vehicle_number_by_type


# This function may be replaced by the "power_and_output" function from eFlips-eval, output
# Function to obtain the amount of charging stations and slots grouped by charging_type
def get_charging_stations_and_slots_count(session, scenario):
    # Getting the amount of chargers grouped by charging type (DEPOT or OPPORTUNITY).
    result= session.query(
        Station.scenario_id,
        Station.charge_type,
        func.count(Station.id),
        func.sum(Station.amount_charging_places)
    ).filter(
        Station.scenario_id == scenario.id,
        Station.amount_charging_places.isnot(None),
        Station.charge_type.isnot(None)
    ).group_by(
        Station.charge_type,
        Station.scenario_id
    ).all()
    # The result is written in a list which can be used by the make_parameter_list function.
    chargers: list[tuple[int, str, int]]= []
    for i in result:
        chargers.append((i[0], i[1]+" Station", i[2]))
        chargers.append((i[0], i[1]+" Slot", i[3]))
    return chargers


""" Get the total fuel (Energy) consumption from the database. As the scenario only simulates a time period 
of 7 days, the energy consumption must be multiplied. """
def get_total_energy_consumption(session, scenario):
    """
    This method gets the total energy consumption for the given scenario from the session provided.
    :param session: A session object.
    :param scenario: A scenario object.
    :return: A tuple including the scenario id and the total energy consumption in kWh.
    """

    # obtain the energy consumption as the difference in state of charge before and after the charging events.
    # This difference ist the multiplied by the battery capacity and divided by the charging efficiency
    # to account for the Energy lost during charging.
    result = session.query(
        func.sum((Event.soc_end - Event.soc_start) * VehicleType.battery_capacity/VehicleType.charging_efficiency)
    ).select_from(
        Event
    ).join(
        VehicleType, Event.vehicle_type_id == VehicleType.id
    ).filter(
        or_(Event.event_type == 'CHARGING_DEPOT',
            Event.event_type == 'CHARGING_OPPORTUNITY'),
        Event.scenario_id == scenario.id
    ).one()
    # Calculate the annual energy consumption
    energy_consumption = result[0] * functions.sim_period_to_year(session=session, scenario=scenario)
    return (scenario.id, energy_consumption)


"""Get the fleet mileage by vehicle type in km."""
def get_fleet_mileage_by_vehicle_type(session, scenario):
    """
    This method gets the annual fleet mileage sorted by vehicle type from the session provided.
    :param session: A session object.
    :param scenario: A scenario object.
    :return: A list of tuples including the scenario id, the name of the respective vehicle type and the total fleet mileage of the respective vehicle type in km.
    """
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
def get_total_fleet_mileage(session, scenario):
    mileage_by_vtype = get_fleet_mileage_by_vehicle_type(session, scenario)
    # Next, the total fleet mileage over the simulation period is calculated
    total_mileage = sum([t[2] for t in mileage_by_vtype])
    return (scenario.id, total_mileage)


""" Calculate the driver hours  """
def get_driver_hours(session, scenario):
    result = session.query(
        func.sum(Event.time_end - Event.time_start)
    ).filter(
        Event.scenario_id == scenario.id,
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
        scenario.id,
        VehicleType.name,
        VehicleType.battery_capacity
    ).filter(
        VehicleType.scenario_id == scenario.id
    ).all()
    return result
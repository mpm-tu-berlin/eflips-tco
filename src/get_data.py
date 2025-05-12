import datetime
from typing import List, Tuple, Any
from eflips.model import Vehicle, Station, Event, VehicleType, Route, Trip, BatteryType, Area, Process, \
    ChargingPointType, Depot
from sqlalchemy import or_, and_
from sqlalchemy import func
import numpy as np
import functions
import time

from eflips.eval.output.prepare import power_and_occupancy


# Calculating the number of vehicles per vehicle type.
def get_vehicle_count_by_type_tco_parameters(session, scenario):
    """
    This method gets the number of vehicles sorted by the vehicle type from the session provided.

    :param session: A session object.
    :param scenario: A scenario object.
    :return: A list of tuples including the scenario id of the calculated scenario, the name of the vehicle type and
        the number of vehicles of the respective vehicle type including the tco_parameters of the respective vehicle type.
    """
    # Gets the vehicle types used in the current scenario
    vehicle_types = scenario.vehicle_types

    # Create empty list in which the number and type of buses are listed.
    vehicle_number_by_type: list[tuple[int, str, int, dict]] = []

    # Counts all vehicles and saves them in the list including Scenario.id and VehicleType.name
    for vt in vehicle_types:
        vt_count = session.query(
            Vehicle,
        ).filter(
            Vehicle.scenario == scenario,
            Vehicle.vehicle_type_id == vt.id
        ).count()
        vehicle_number_by_type.append((scenario.id, vt.name, vt_count, vt.tco_parameters))

    # return the list
    return vehicle_number_by_type


# This function returns the number of the charging slots and stations including the tco parameters grouped by the
# charging infrastructure type.
def get_charging_stations_and_slots_tco(session, scenario):
    # calculate the number of all charging infrastructure in all areas.
    charging_infra_dict = {}

    # Charging slots in the depot

    # find the areas in which the charging takes place.
    areas_tco= (session.query(
        Area,
        ChargingPointType
    ).join(
        ChargingPointType, ChargingPointType.id == Area.charging_point_type_id
    ).join(
        Depot, Depot.id == Area.depot_id
    ).filter(
        Area.scenario_id == scenario.id,
        Area.processes.any(
            and_(
                Process.electric_power.isnot(None),
                Process.duration.is_(None),
            )
        )
    ).all()
            )

    # Add the number of charging slots and have them sorted by type
    for area in areas_tco:
        num_charging_slots = power_and_occupancy(area.Area.id, session)["occupancy_charging"].max()
        # Add the number of charging slots to the respective entry in the dictionary.
        if area.ChargingPointType.tco_parameters["name"] in charging_infra_dict:
            num_type = charging_infra_dict[area.ChargingPointType.tco_parameters["name"]].get("number_of_type")
            charging_infra_dict[area.ChargingPointType.tco_parameters["name"]]["number_of_type"] = int(num_type+num_charging_slots)
        else:
            charging_infra_dict.update({area.ChargingPointType.tco_parameters["name"]:
                {"number_of_type": int(num_charging_slots),
                 "tco_parameters": area.ChargingPointType.tco_parameters}})

    # Get the charging slots in the OC stations

    # Get all opportunity charging stations
    oc_stations = session.query(
        Station,
        ChargingPointType
    ).join(
        ChargingPointType, ChargingPointType.id == Station.charging_point_type_id # join only the OC slots, as this is NULL for all depot Charging slots.
    ).filter(
        Station.scenario_id == scenario.id
    ).all()

    # Get the number of OC slots and add all required data to the charging infrastructure dictionary.
    start_time = time.time() # measure the runtime
    for station in oc_stations:

        # Get the number of charging slots in the station.
        num_oc_slots = power_and_occupancy(area_id=None, session=session, station_id=station.Station.id)[
        "occupancy_charging"].max()

        # Check, whether the type of charging slot is already in the dictionary and add the number to the dictionary.
        if station.ChargingPointType.tco_parameters["name"] in charging_infra_dict:
            num_type = charging_infra_dict[station.ChargingPointType.tco_parameters["name"]].get("number_of_type")
            charging_infra_dict[station.ChargingPointType.tco_parameters["name"]]["number_of_type"] = int(num_type + num_oc_slots)
        else:
            charging_infra_dict.update({station.ChargingPointType.tco_parameters["name"]:
                {"number_of_type": int(num_oc_slots),"tco_parameters": station.ChargingPointType.tco_parameters}})

    # runtime test
    end_time = time.time()
    # print the runtime
    print("\nRuntime calculation of the number of OC charging slots: {} seconds\n".format((end_time-start_time)))

    # Get th charging stations and the respective tco parameters.
    stations = session.query(
        Station.charge_type,
        func.count(Station.id),
        Station.tco_parameters
    ).filter(
        Station.scenario_id == scenario.id,
        Station.is_electrified
    ).group_by(
        Station.tco_parameters,
        Station.charge_type
    ).all()

    # Add all stations grouped by type and tco parameters to the infrastructure dictionary.
    for station in stations:
        charging_infra_dict.update({station.tco_parameters["name"]:
            {"number_of_type": int(station[1]), "tco_parameters": station.tco_parameters}})

    # return the dictionary
    return charging_infra_dict


# Get the total fuel / Energy consumption from the database.
def get_total_energy_consumption(session, scenario):
    """
    This method gets the total energy consumption for the given scenario from the session provided.
    :param session: A session object.
    :param scenario: A scenario object.
    :return: The total energy consumption in kWh.
    """

    # Obtain the energy consumption as the difference in state of charge before and after the charging events.
    # This difference is then multiplied by the battery capacity and divided by the charging efficiency
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

    return energy_consumption


# Get the fleet mileage by vehicle type in km.
def get_fleet_mileage_by_vehicle_type(session, scenario):
    """
    This method gets the annual fleet mileage sorted by vehicle type from the session provided.

    :param session: A session object.
    :param scenario: A scenario object.
    :return: A list of tuples including the scenario id, the name of the respective vehicle type and the total fleet mileage of the respective vehicle type in km.
    """

    # Get the sum of route distances grouped by VehicleType
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

    #Calculate the total mileage by vehicle type over one year.
    annual_mileage_by_vtype: list[tuple[int, str, float]] = []
    for i in range(len(result)):
        # Add the respective tuple to the list.
        annual_mileage_by_vtype.append(
            (result[i][0], result[i][1], result[i][2]*functions.sim_period_to_year(session, scenario)/1000)
        )

    return annual_mileage_by_vtype


# Calculate the total fleet mileage not grouped by vehicle type.
def get_total_fleet_mileage(session, scenario):

    # Get the annual fllet mileage grouped by vehicle type.
    mileage_by_vtype = get_fleet_mileage_by_vehicle_type(session, scenario)

    # Next, the total annual fleet mileage is calculated
    total_mileage = sum([t[2] for t in mileage_by_vtype])

    return total_mileage


# Calculate the annual driver hours.
def get_driver_hours(session, scenario):
    # Get the driver hours over the simulation period as the sum of the duration of all driving events.
    result = session.query(
        func.sum(Event.time_end - Event.time_start)
    ).filter(
        Event.scenario_id == scenario.id,
        or_(Event.event_type == 'DRIVING', Event.event_type == 'CHARGING_OPPORTUNITY')
    ).one()
    # Annual driver hours are calculated
    driver_hours = functions.sim_period_to_year(session = session, scenario = scenario)* result[0].total_seconds() / 3600
    return driver_hours


# This method returns the simulation duration using the earliest and latest Event.
# It is used by the functions.sim_period_to_year() function.
def get_simulation_period(session, scenario):
    result = session.query(
        func.min(Event.time_start),
        func.max(Event.time_end)
    ).filter(
    Event.scenario_id == scenario.id
    ).one()
    return result[1]-result[0]


# This is a method, which returns the battery size and its tco parameters by vehicle type.
def get_battery_size_tco(session, scenario):
    result = session.query(
        scenario.id,
        VehicleType.name,
        VehicleType.battery_capacity,
        BatteryType.tco_parameters
    ).join(
        BatteryType, BatteryType.id == VehicleType.battery_type_id
    ).filter(
        VehicleType.scenario_id == scenario.id
    ).all()
    return result
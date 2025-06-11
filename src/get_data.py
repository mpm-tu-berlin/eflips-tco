import datetime
import warnings
from typing import List, Tuple, Any
from eflips.model import Vehicle, Station, Event, VehicleType, Route, Trip, BatteryType, Area, Process, \
    ChargingPointType, Depot
from sqlalchemy import or_, and_
from sqlalchemy import func
import numpy as np
import functions
import time
import warnings as w

from eflips.eval.output.prepare import power_and_occupancy


# Calculating the number of vehicles per vehicle type.
def get_vehicle_count_dict(
        session,
        scenario
):

    # Get the number of vehicles grouped by vehicle type
    result = session.query(
        func.count(Vehicle.id),
        VehicleType.tco_parameters
    ).join(
        Vehicle, Vehicle.vehicle_type_id == VehicleType.id
    ).filter(
        Vehicle.scenario_id == scenario.id
    ).group_by(
        VehicleType.tco_parameters
    ).all()

    # The fleet mileage of the respective vehicle type is also included in the dictionary
    fleet_mileage = get_fleet_mileage_by_vehicle_type(session, scenario)

    # Write the results in a dictionary and return the dictionary
    result_dict = {}
    for number, tco_parameters in result:
        # Get the total annual mileage for the respective vehicle type
        mileage_this_vtype = 0
        for scenario_id, name, mileage in fleet_mileage:
            if name == tco_parameters.get('name'):
                mileage_this_vtype = mileage
                # Break the loop if the respective tco parameters are found.
                break


        # Add the data to the dictionary
        result_dict[(tco_parameters.get("name")+" VEHICLE")] = {
            "procurement_cost": tco_parameters.get("procurement_cost"),
            "useful_life": tco_parameters.get("useful_life"),
            "cost_escalation": tco_parameters.get("cost_escalation"),
            "number_of_assets": number,
            "annual_mileage": mileage_this_vtype,
            #"specific_energy_consumption": (energy_consumption_this_vtype/mileage_this_vtype)
        }
    return result_dict


# This function returns the number of the charging slots and stations including the tco parameters grouped by the
# charging infrastructure type.
def get_charging_stations_and_slots_tco(
        session,
        scenario
):
    """
    This method calculates the number of charging infrastructure required to operate the bus system in the given scenario.

    :param session: A Session object.
    :param scenario: A Scenario object.
    :return: A dictionary including the number of the charging slots and stations including the tco parameters grouped by the charging infrastructure type.
    """

    # calculate the number of all charging infrastructure in all areas.
    charging_infra_dict = {}

    # Charging slots in the depot
    # find the areas in which the charging takes place.
    # This query is the work of my supervisor.
    areas_tco= session.query(
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


    # Add the number of charging slots and have them sorted by type
    for area in areas_tco:
        num_charging_slots = power_and_occupancy(area.Area.id, session)["occupancy_charging"].max()
        # Add the number of charging slots to the respective entry in the dictionary.
        if (area.ChargingPointType.tco_parameters["name"]+" INFRASTRUCTURE") in charging_infra_dict:
            num_type = charging_infra_dict[(area.ChargingPointType.tco_parameters["name"]+" INFRASTRUCTURE")].get("number_of_assets")
            charging_infra_dict[(area.ChargingPointType.tco_parameters["name"]+" INFRASTRUCTURE")]["number_of_assets"] = int(num_type+num_charging_slots)
        else:
            charging_infra_dict.update({(area.ChargingPointType.tco_parameters["name"]+" INFRASTRUCTURE"):
                {"procurement_cost": area.ChargingPointType.tco_parameters.get("procurement_cost"),
                 "useful_life": area.ChargingPointType.tco_parameters.get("useful_life"),
                 "cost_escalation": area.ChargingPointType.tco_parameters.get("cost_escalation"),
                 "number_of_assets": int(num_charging_slots)
                 }})

    # Get the charging slots in the OC stations

    # Get all opportunity charging stations
    oc_stations = session.query(
        Station,
        ChargingPointType
    ).join(
        ChargingPointType, ChargingPointType.id == Station.charging_point_type_id # join only the OC slots, as this is NULL for all depot Charging slots.
    ).join(
        Event, Event.station_id == Station.id
    ).filter(
        Station.scenario_id == scenario.id,
        Event.event_type == 'CHARGING_OPPORTUNITY'
    ).all()

    # Get the number of OC slots and add all required data to the charging infrastructure dictionary.
    for station in oc_stations:
        # Get the number of charging slots in the station.
        try:
            num_oc_slots = power_and_occupancy(area_id=None, session=session, station_id=station.Station.id)[
            "occupancy_charging"].max()

            # Check, whether the type of charging slot is already in the dictionary and add the number to the dictionary.
            if (station.ChargingPointType.tco_parameters["name"]+ " INFRASTRUCTURE") in charging_infra_dict:
                num_type = charging_infra_dict[(station.ChargingPointType.tco_parameters["name"]+ " INFRASTRUCTURE")].get("number_of_assets")
                charging_infra_dict[(station.ChargingPointType.tco_parameters["name"]+ " INFRASTRUCTURE")]["number_of_assets"] = int(num_type + num_oc_slots)
            else:
                charging_infra_dict.update({(station.ChargingPointType.tco_parameters["name"]+ " INFRASTRUCTURE"):
                    {"procurement_cost": station.ChargingPointType.tco_parameters.get("procurement_cost"),
                     "useful_life": station.ChargingPointType.tco_parameters.get("useful_life"),
                     "cost_escalation": station.ChargingPointType.tco_parameters.get("cost_escalation"),
                     "number_of_assets": int(num_oc_slots)
                     }})

        except ValueError:
            w.warn("No charging slots have been found for the opportunity charging stations. They are not considered in the calculation.")


    # Get the charging stations and the respective tco parameters.
    stations = session.query(
        func.count(func.distinct(Station.id)),
        Station.tco_parameters
    ).join(
        Event, Event.station_id == Station.id
    ).filter(
        Station.scenario_id == scenario.id,
        Station.is_electrified,
        or_(
            Event.event_type == 'CHARGING_OPPORTUNITY',
            Event.event_type == 'CHARGING_DEPOT'
        )
    ).group_by(
        Station.tco_parameters
    ).all()

    # Add all stations grouped by type and tco parameters to the infrastructure dictionary.
    for station in stations:
        charging_infra_dict.update({(station.tco_parameters["name"]+" INFRASTRUCTURE"):
            {"procurement_cost": station.tco_parameters.get("procurement_cost"),
             "useful_life": station.tco_parameters.get("useful_life"),
             "cost_escalation": station.tco_parameters.get("cost_escalation"),
             "number_of_assets": int(station[0])}})

    # return the dictionary
    return charging_infra_dict


# Get the total fuel / Energy consumption from the database.
def get_total_energy_consumption(
        session,
        scenario
):
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
    energy_consumption = result[0] * get_simulation_period(session=session, scenario=scenario)[1]

    return energy_consumption


# Get the fleet mileage by vehicle type in km.
def get_fleet_mileage_by_vehicle_type(
        session,
        scenario
):
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
            (result[i][0], result[i][1], result[i][2]*get_simulation_period(session, scenario)[1]/1000)
        )

    return annual_mileage_by_vtype

def get_passenger_mileage(session, scenario):
    result = session.query(
        func.sum(Route.distance)
    ).join(
        Trip, Route.id == Trip.route_id
    ).join(
        Event, Event.trip_id == Trip.id
    ).filter(
        Event.scenario_id == scenario.id,
        Trip.trip_type == "PASSENGER"
    ).one()

    annual_mileage = result[0]*get_simulation_period(session, scenario)[1]/1000
    return annual_mileage


# Calculate the annual driver hours.
def get_driver_hours(
        session,
        scenario
):
    # Get the driver hours over the simulation period as the sum of the duration of all driving events.
    result = session.query(
        func.sum(Event.time_end - Event.time_start)
    ).filter(
        Event.scenario_id == scenario.id,
        or_(Event.event_type == 'DRIVING', Event.event_type == 'CHARGING_OPPORTUNITY')
    ).one()
    # Annual driver hours are calculated
    driver_hours = get_simulation_period(session = session, scenario = scenario)[1]* result[0].total_seconds() / 3600
    return driver_hours


# This method returns the simulation duration using the earliest and latest Event.
def get_simulation_period(
        session,
        scenario
):
    """
    This method returns the simulation duration using the time_start of the earliest and the time_end of the latest
        driving event. Besides that a factor is calculated which can be multiplied by all considered input parameters
        to obtain the annual quantity of the respective parameter.
    :param session: A session object.
    :param scenario: The considered scenario.
    :return: A tuple of the simulation duration and the factor needed to obtain annual quantities.
    """
    result = session.query(
        func.min(Event.time_start),
        func.max(Event.time_end)
    ).filter(
        Event.scenario_id == scenario.id,
        Event.event_type == 'DRIVING'
    ).one()
    simulation_period = result[1]-result[0]
    factor  = 365.25 / (simulation_period.total_seconds()/86400)
    return (simulation_period, factor)


# This is a method, which returns the battery size and its tco parameters by vehicle type.
def get_battery_size_dict(
        session,
        scenario
):
    """
    This method gets the battery size from the session provided and returns it in a dictionary.
    :param session: A session object.
    :param scenario: A scenario object.
    :return: A dictionary including the name if the vehicle using this battery, battery capacity and the tco parameters.
    """
    result = session.query(
        VehicleType.name,
        VehicleType.battery_capacity,
        BatteryType.tco_parameters,
        func.count(Vehicle.id)
    ).join(
        BatteryType, BatteryType.id == VehicleType.battery_type_id
    ).join(
        Vehicle, Vehicle.vehicle_type_id == VehicleType.id
    ).filter(
        VehicleType.scenario_id == scenario.id
    ).group_by(
        VehicleType.name, VehicleType.battery_capacity, BatteryType.tco_parameters
    ).all()

    result_dict = {}
    for vehicle_type_name, battery_capacity, tco, number in result:
        result_dict[(vehicle_type_name+" BATTERY")] = {
            "procurement_cost": (tco.get("procurement_cost", 0)*battery_capacity), # get the procurement cost per battery
            "useful_life": tco.get("useful_life", 0),
            "cost_escalation": tco.get("cost_escalation", 0),
            "battery_capacity": battery_capacity,
            "number_of_assets": number
        }
    return result_dict
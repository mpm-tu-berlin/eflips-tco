import datetime
import warnings
from typing import List, Tuple, Any, Dict
from eflips.model import (
    Vehicle,
    Station,
    Event,
    VehicleType,
    Route,
    Trip,
    BatteryType,
    Area,
    Process,
    ChargingPointType,
    Depot,
    ChargeType,
)
from sqlalchemy import or_, and_
from sqlalchemy import func
import numpy as np
import time
import warnings as w

from eflips.tco.cost_items import CapexItemType, CapexItem, OpexItem
from eflips.eval.output.prepare import power_and_occupancy


def load_capex_items_vehicle(session, scenario):
    # Get the number of vehicles grouped by vehicle type
    list_vt_count_parameter = (
        session.query(VehicleType, func.count(Vehicle.id), VehicleType.tco_parameters)
        .join(Vehicle, Vehicle.vehicle_type_id == VehicleType.id)
        .filter(Vehicle.scenario_id == scenario.id)
        .group_by(VehicleType.id)
        .all()
    )

    # Write the results in a dictionary and return the dictionary
    list_vt_asset = []
    for vehicle_type, vehicle_count, tco_parameters in list_vt_count_parameter:
        # Get the total annual mileage for the respective vehicle type
        asset_this_vtype = CapexItem(
            name=vehicle_type.name,
            asset_type=CapexItemType.VEHICLE,
            useful_life=tco_parameters["useful_life"],
            procurement_cost=tco_parameters["procurement_cost"],
            cost_escalation=tco_parameters["cost_escalation"],
            quantity=vehicle_count,
        )
        list_vt_asset.append(asset_this_vtype)

    return list_vt_asset


def load_capex_items_battery(session, scenario):
    """
    This method gets the battery size from the session provided and returns it in a dictionary.
    :param session: A session object.
    :param scenario: A scenario object.
    :return: A dictionary including the name if the vehicle using this battery, battery capacity and the tco parameters.
    """
    list_vt_battery = (
        session.query(
            VehicleType,
            VehicleType.battery_capacity,
            BatteryType.tco_parameters,
            func.count(Vehicle.id),
        )
        .join(BatteryType, BatteryType.id == VehicleType.battery_type_id)
        .join(Vehicle, Vehicle.vehicle_type_id == VehicleType.id)
        .filter(VehicleType.scenario_id == scenario.id)
        .group_by(VehicleType.id, VehicleType.battery_capacity, BatteryType.id)
        .all()
    )

    list_battery_asset = []
    for vehicle_type, battery_capacity, tco_battery, number in list_vt_battery:
        asset_this_battery = CapexItem(
            name="Battery type " + str(vehicle_type.battery_type_id),
            asset_type=CapexItemType.BATTERY,
            useful_life=tco_battery["useful_life"],
            procurement_cost=tco_battery["procurement_cost"] * battery_capacity,
            cost_escalation=tco_battery["cost_escalation"],
            quantity=number,
        )
        list_battery_asset.append(asset_this_battery)
    return list_battery_asset


# This function returns the number of the charging slots and stations including the tco parameters grouped by the
# charging infrastructure type.
def load_capex_items_infrastructure(session, scenario):
    """
    This method calculates the number of charging infrastructure required to operate the bus system in the given scenario.

    :param session: A Session object.
    :param scenario: A Scenario object.
    :return: A dictionary including the number of the charging slots and stations including the tco parameters grouped by the charging infrastructure type.
    """

    charging_point_types = scenario.charging_point_types
    list_asset_charging_points = []

    for charging_point_type in charging_point_types:
        total_count = 0
        if charging_point_type.areas is not None:
            for area in charging_point_type.areas:
                try:
                    num_dc_slots = power_and_occupancy(
                        area_id=area.id, session=session
                    )["occupancy_charging"].max()
                    total_count += num_dc_slots
                except ValueError:
                    w.warn(
                        f"No charging slots have been found for the depot charging stations of type "
                        f"{charging_point_type.name}. They are not considered in the calculation."
                    )

        if charging_point_type.stations is not None:
            for station in charging_point_type.stations:
                try:
                    num_oc_slots = power_and_occupancy(
                        area_id=None, session=session, station_id=station.id
                    )["occupancy_charging"].max()
                    total_count += num_oc_slots
                except ValueError:
                    w.warn(
                        f"No charging slots have been found for the opportunity charging stations of type "
                        f"{charging_point_type.name}. They are not considered in the calculation."
                    )

        asset_charging_point_type = CapexItem(
            name=charging_point_type.tco_parameters["name"],
            asset_type=CapexItemType.CHARGING_POINT,
            useful_life=charging_point_type.tco_parameters["useful_life"],
            procurement_cost=charging_point_type.tco_parameters["procurement_cost"],
            cost_escalation=charging_point_type.tco_parameters["cost_escalation"],
            quantity=int(total_count),
        )
        list_asset_charging_points.append(asset_charging_point_type)

    # Get the charging stations and the respective tco parameters.
    stations = (
        session.query(
            Station.charge_type,
            func.count(func.distinct(Station.id)),
            Station.tco_parameters,
        )
        .join(Event, Event.station_id == Station.id)
        .filter(
            Station.scenario_id == scenario.id,
            Station.is_electrified,
            or_(
                Event.event_type == "CHARGING_OPPORTUNITY",
                Event.event_type == "CHARGING_DEPOT",
            ),
        )
        .group_by(Station.tco_parameters, Station.charge_type)
        .all()
    )

    # Add all stations grouped by type and tco parameters to the infrastructure dictionary.
    for station_charge_type, station_count, tco_parameters in stations:
        asset_station = CapexItem(
            name="Station" if station_charge_type == ChargeType.oppb else "Depot",
            asset_type=CapexItemType.INFRASTRUCTURE,
            useful_life=tco_parameters["useful_life"],
            procurement_cost=tco_parameters["procurement_cost"],
            cost_escalation=tco_parameters["cost_escalation"],
            quantity=int(station_count),
        )
        list_asset_charging_points.append(asset_station)

    # return the dictionary
    return list_asset_charging_points


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
    result = (
        session.query(
            func.sum(
                (Event.soc_end - Event.soc_start)
                * VehicleType.battery_capacity
                / VehicleType.charging_efficiency
            )
        )
        .select_from(Event)
        .join(VehicleType, Event.vehicle_type_id == VehicleType.id)
        .filter(
            or_(
                Event.event_type == "CHARGING_DEPOT",
                Event.event_type == "CHARGING_OPPORTUNITY",
            ),
            Event.scenario_id == scenario.id,
        )
        .one()
    )

    # Calculate the annual energy consumption
    energy_consumption = (
        result[0] * get_simulation_period(session=session, scenario=scenario)[1]
    )

    return energy_consumption


# Get the fleet mileage by vehicle type in km.

def get_annual_fleet_mileage(session, scenario) -> float:
    """
    This method gets the annual fleet mileage from the session provided.

    :param session: A session object.
    :param scenario: A scenario object.
    :return: The total annual fleet mileage in km.
    """

    simulation_period, period_per_year = get_simulation_period(
        session=session, scenario=scenario
    )

    total_simulated_mileage = (session.query(func.sum(Route.distance))
        .join(Trip, Route.id == Trip.route_id)
        .filter(Trip.scenario_id == scenario.id)
        .scalar())

    return total_simulated_mileage * period_per_year / 1000  # Convert to km


# Calculate the annual driver hours.
def calculate_total_driver_hours(
    session, scenario, annual_hours_per_driver=1600, buffer=0.1
):
    # Get the driver hours over the simulation period as the sum of the duration of all driving events.
    driver_hours = (
        session.query(func.sum(Event.time_end - Event.time_start))
        .filter(
            Event.scenario_id == scenario.id,
            or_(
                Event.event_type == "DRIVING",
                Event.event_type == "CHARGING_OPPORTUNITY",
            ),
        )
        .one()[0]
    )
    # Annual driver hours are calculated
    annual_driver_hours = (
        get_simulation_period(session=session, scenario=scenario)[1]
        * driver_hours.total_seconds()
        / 3600
    )

    number_drivers = (annual_driver_hours * (1 + buffer)) // annual_hours_per_driver
    actual_driver_hours = annual_hours_per_driver * (number_drivers + 1)
    return actual_driver_hours


# This method returns the simulation duration using the earliest and latest Event.
def get_simulation_period(session, scenario):
    """
    This method returns the simulation duration using the time_start of the earliest and the time_end of the latest
        driving event. Besides that a factor is calculated which can be multiplied by all considered input parameters
        to obtain the annual quantity of the respective parameter.
    :param session: A session object.
    :param scenario: The considered scenario.
    :return: A tuple of the simulation duration and the factor needed to obtain annual quantities.
    """
    result = (
        session.query(func.min(Event.time_start), func.max(Event.time_end))
        .filter(Event.scenario_id == scenario.id, Event.event_type == "DRIVING")
        .one()
    )
    simulation_period = result[1] - result[0]
    periods_per_year = 365.25 / (simulation_period.total_seconds() / 86400)
    return simulation_period, periods_per_year


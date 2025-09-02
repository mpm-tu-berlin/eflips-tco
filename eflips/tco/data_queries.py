import datetime
import warnings
from typing import List, Tuple, Any, Dict, Optional, Union
from eflips.model import (
    Vehicle,
    Station,
    VehicleType,
    Route,
    Trip,
    TripType,
    BatteryType,
    ChargeType,
    Scenario,
    ChargingPointType,
    Area,
    Process,
    Event,
    EventType,
    Depot, Rotation,
)

from sqlalchemy import or_, and_, distinct
from sqlalchemy import func

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import numpy as np
import time
import warnings as w

from eflips.tco.cost_items import CapexItemType, CapexItem, OpexItem
from eflips.tco.util import create_session
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
            type=CapexItemType.VEHICLE,
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
            type=CapexItemType.BATTERY,
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
        if total_count != 0:
            asset_charging_point_type = CapexItem(
                name=charging_point_type.tco_parameters["name"],
                type=CapexItemType.CHARGING_POINT,
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
            type=CapexItemType.INFRASTRUCTURE,
            useful_life=tco_parameters["useful_life"],
            procurement_cost=tco_parameters["procurement_cost"],
            cost_escalation=tco_parameters["cost_escalation"],
            quantity=int(station_count),
        )
        list_asset_charging_points.append(asset_station)

    # return the dictionary
    return list_asset_charging_points


# Get the total fuel / Energy consumption from the database.
def calc_energy_consumption_simulated(session, scenario):
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

    total_simulated_mileage = (
        session.query(func.sum(Route.distance))
        .join(Trip, Route.id == Trip.route_id)
        .filter(Trip.scenario_id == scenario.id)
        .scalar()
    )

    # TODO annual fleet mileage slightly different from the original (by 1e-5?). Need validation

    return total_simulated_mileage * period_per_year / 1000  # Convert to km

def get_mileage_per_vehicle_type(session, scenario) -> Dict[int, Tuple[float, float]]:
    """

    """

    vt_mileage = (session.query(Rotation.vehicle_type_id, func.sum(Route.distance)).join(Trip, Trip.route_id == Route.id).
                  join(Rotation, Trip.rotation_id == Rotation.id).
        filter(Rotation.scenario_id == scenario.id).group_by(Rotation.vehicle_type_id).all())



    mileage_per_vt = {}
    for vt, mileage in vt_mileage:
        mileage_per_vt[str(vt)] = mileage / 1000 * get_simulation_period(session=session, scenario=scenario)[1]

    return mileage_per_vt




# Calculate the annual driver hours.
def calculate_total_driver_hours(
    session, scenario, annual_hours_per_driver=1600, buffer=0.1
):
    # Get the driver hours over the simulation period as the sum of the duration of all driving events.

    driver_hours = datetime.timedelta(seconds=0)
    driving_and_opcharge_events = session.query(Event).filter(
        Event.scenario_id == scenario.id,
        or_(
            Event.event_type == "DRIVING",
            Event.event_type == "CHARGING_OPPORTUNITY",
        ),
    ).all()

    for event in driving_and_opcharge_events:
        driver_hours += event.time_end - event.time_start
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

    # TODO match the temperature with time and accordingly scale down the consumption
    result = (
        session.query(func.min(Event.time_start), func.max(Event.time_end))
        .filter(Event.scenario_id == scenario.id, Event.event_type == "DRIVING")
        .one()
    )
    simulation_period = result[1] - result[0]
    periods_per_year = 365.25 / (simulation_period.total_seconds() / 86400)
    return simulation_period, periods_per_year


def init_tco_parameters(
    scenario: Union[Scenario, int, Any],
    database_url: Optional[str] = None,
    scenario_tco_parameters: Optional[Dict[str, Any]] = None,
    vehicle_types: Optional[List[Dict[str, Any]]] = None,
    battery_types: Optional[List[Dict[str, Any]]] = None,
    charging_point_types: Optional[List[Dict[str, Any]]] = None,
    charging_infrastructure: Optional[List[Dict[str, Any]]] = None,
):
    """
    Initialize the TCO parameters for the given scenario in the database.
    :param scenario_id: The ID of the scenario to initialize.
    :param database_url: The database URL to connect to.
    :param scenario_tco_parameters: A dictionary containing the TCO parameters for the scenario.
    :param vehicle_types: A list of dictionaries containing TCO parameters for vehicle types. Must include 'id'
        referring to the VehicleType stored in the database.
    :param battery_types: A list of dictionaries containing TCO parameters for battery types. Must include 'id'
        (pointing to existing BatteryType) or 'vehicle_type_id' (point to an existing VehicleType) to create a new
        BatteryType used by the vehicle type.
    :param charging_point_types: A list of dictionaries containing TCO parameters for charging point types. Must include
        'id' (pointing to existing ChargingPointType) or 'type' (to create a new ChargingPointType).
    :param charging_infrastructure: A list of dictionaries containing TCO parameters for charging infrastructure. Must
        include 'type' (either 'station' or 'depot') to specify the type of charging infrastructure.

    """

    tco_keys = {"name", "procurement_cost", "useful_life", "cost_escalation"}

    with create_session(scenario, database_url) as (session, scenario):
        scenario.tco_parameters = scenario_tco_parameters
        # Add tco parameters to vehicle types
        if vehicle_types is not None:
            for vt_info in vehicle_types:
                vt = (
                    session.query(VehicleType)
                    .filter(VehicleType.id == vt_info.get("id"), VehicleType.scenario_id == scenario.id)
                    .all()
                )


                assert len(vt) == 1, (f"There should be only one VehicleType with id {vt_info.get('id')} found in scenario "
                                      f"{scenario.id}. Now there are {len(vt)}.")

                vt = vt[0]
                vt_tco_parameters = {
                    key: vt_info.get(key) for key in tco_keys if key in vt_info
                }
                vt.tco_parameters = vt_tco_parameters

        # Add tco parameters to battery types
        if battery_types is not None:
            for bt_info in battery_types:
                bt_tco_parameters = {
                    key: bt_info.get(key) for key in tco_keys if key in bt_info
                }

                if "id" not in bt_info:
                    new_battery_type = BatteryType(
                        scenario_id=scenario.id,
                        specific_mass=bt_info.get("specific_mass", 1.0),
                        chemistry=bt_info.get("chemistry", "unknown"),
                        tco_parameters=bt_tco_parameters,
                    )
                    session.add(new_battery_type)

                    vehicle_type_id = bt_info.get("vehicle_type_id")
                    vehicle_type = session.query(VehicleType).filter(
                        VehicleType.id == vehicle_type_id
                    ).one()
                    assert vehicle_type.scenario_id == scenario.id, (
                        f"VehicleType with id {vehicle_type_id} is not in scenario {scenario.id}. Please add this battery to the correct VehicleType."
                    )
                    vehicle_type.battery_type = new_battery_type

                else:
                    battery_type_id = bt_info.get("id")
                    battery_type = (
                        session.query(BatteryType)
                        .filter(BatteryType.id == battery_type_id, BatteryType.scenario_id == scenario.id,)
                        .all()
                    )
                    assert len(battery_type) == 1, (f"There should be only one BatteryType with id {battery_type_id} found in scenario "
                                      f"{scenario.id}. Now there are {len(battery_type)}.")

                    battery_type = battery_type[0]
                    battery_type.tco_parameters = bt_tco_parameters

        # Add tco parameters to charging point types

        if charging_point_types is not None:
            for cp_info in charging_point_types:
                cp_tco_parameters = {
                    key: cp_info.get(key) for key in tco_keys if key in cp_info
                }
                if "id" not in cp_info:
                    new_cp_type = ChargingPointType(
                        name=cp_info.get("name", "Unknown Charging Point"),
                        scenario_id=scenario.id,
                        tco_parameters=cp_tco_parameters,
                    )
                    session.add(new_cp_type)

                    match cp_info.get("type"):
                        case "depot":
                            # Add to areas
                            charging_areas = session.query(Area).filter(
                                Area.processes.any(Process.electric_power.isnot(None)),
                                Area.scenario_id == scenario.id,
                            )
                            for area in charging_areas:
                                area.charging_point_type = new_cp_type
                        case "opportunity":
                            # Add to stations
                            charging_station_ids = (
                                session.query(distinct(Event.station_id))
                                .filter(
                                    Event.event_type == EventType.CHARGING_OPPORTUNITY,
                                    Event.scenario_id == scenario.id,
                                )
                                .all()
                            )
                            if len(charging_station_ids) != 0:
                                for station_id in charging_station_ids:
                                    station = (
                                        session.query(Station)
                                        .filter(Station.id == station_id[0])
                                        .one()
                                    )
                                    station.charging_point_type = new_cp_type
                        case _:
                            raise ValueError(
                                f"Unknown charging point type: {cp_info.get('type')}"
                            )
                else:
                    charging_point_type_id = cp_info.get("id")
                    charging_point_type = (
                        session.query(ChargingPointType)
                        .filter(ChargingPointType.id == charging_point_type_id, ChargingPointType.scenario_id == scenario.id)
                        .all()
                    )
                    assert len(charging_point_type)==1, (f"There should be only one ChargingPointType with id {charging_point_type_id} found in scenario "
                                      f"{scenario.id}. Now there are {len(charging_point_type)}.")

                    charging_point_type = charging_point_type[0]
                    charging_point_type.tco_parameters = cp_tco_parameters

        # Add tco parameters to charging infrastructure
        if charging_infrastructure is not None:
            for infra_info in charging_infrastructure:

                infra_tco_parameters = {
                    key: infra_info.get(key) for key in tco_keys if key in infra_info
                }

                match infra_info.get("type"):
                    case "station":
                        charging_station_ids = (
                            session.query(distinct(Event.station_id))
                            .filter(
                                Event.event_type == EventType.CHARGING_OPPORTUNITY,
                                Event.scenario_id == scenario.id,
                            )
                            .all()
                        )
                        for station_id in charging_station_ids:
                            station = (
                                session.query(Station)
                                .filter(Station.id == station_id[0])
                                .one()
                            )
                            station.tco_parameters = infra_tco_parameters
                    case "depot":
                        depot_stations = (
                            session.query(Depot.station_id)
                            .filter(Depot.scenario_id == scenario.id)
                            .all()
                        )
                        for station_id in depot_stations:
                            station = (
                                session.query(Station)
                                .filter(Station.id == station_id[0])
                                .one()
                            )
                            station.tco_parameters = infra_tco_parameters
                    case _:
                        raise ValueError(
                            f"Unknown infrastructure type: {infra_info.get('type')}"
                        )

        session.commit()

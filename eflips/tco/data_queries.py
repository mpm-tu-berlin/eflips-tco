import datetime
import warnings
from typing import List, Tuple, Any, Dict, Optional, Union
from eflips.model import (
    Vehicle,
    Station,
    VehicleType,
    Route,
    Trip,
    BatteryType,
    ChargeType,
    Scenario,
    ChargingPointType,
    Area,
    Process,
    Event,
    EventType,
    Depot,
    Rotation,
)

from sqlalchemy import or_, and_, distinct
from sqlalchemy import func

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
    list_asset_charging_infra = []

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
            list_asset_charging_infra.append(asset_charging_point_type)

    # Get the charging stations and the respective tco parameters.


    depots = (
        session.query(
            func.count(func.distinct(Station.id)),
            Station.tco_parameters,
        )
        .join(Event, Event.station_id == Station.id)
        .filter(
            Station.scenario_id == scenario.id,
            or_(
                Event.event_type == "CHARGING_DEPOT",
            ),
        )
        .group_by(Station.tco_parameters)
        .all()
    )

    stations = (
        session.query(
            func.count(func.distinct(Station.id)),
            Station.tco_parameters,
        )
        .join(Event, Event.station_id == Station.id)
        .filter(
            Station.scenario_id == scenario.id,
            or_(
                Event.event_type == "CHARGING_OPPORTUNITY",
            ),
        )
        .group_by(Station.tco_parameters)
        .all()
    )




    # Add all stations grouped by type and tco parameters to the infrastructure dictionary.

    for depot_count, tco_parameters in depots:
        asset_depot = CapexItem(
            name="Depot",
            type=CapexItemType.INFRASTRUCTURE,
            useful_life=tco_parameters["useful_life"],
            procurement_cost=tco_parameters["procurement_cost"],
            cost_escalation=tco_parameters["cost_escalation"],
            quantity=int(depot_count),
        )
        list_asset_charging_infra.append(asset_depot)

    for station_count, tco_parameters in stations:
        asset_station = CapexItem(
            name="Station",
            type=CapexItemType.INFRASTRUCTURE,
            useful_life=tco_parameters["useful_life"],
            procurement_cost=tco_parameters["procurement_cost"],
            cost_escalation=tco_parameters["cost_escalation"],
            quantity=int(station_count),
        )
        list_asset_charging_infra.append(asset_station)

    # return the dictionary
    return list_asset_charging_infra


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
    """ """

    vt_mileage = (
        session.query(Rotation.vehicle_type_id, func.sum(Route.distance))
        .join(Trip, Trip.route_id == Route.id)
        .join(Rotation, Trip.rotation_id == Rotation.id)
        .filter(Rotation.scenario_id == scenario.id)
        .group_by(Rotation.vehicle_type_id)
        .all()
    )

    mileage_per_vt = {}
    for vt, mileage in vt_mileage:
        mileage_per_vt[str(vt)] = (
            mileage
            / 1000
            * get_simulation_period(session=session, scenario=scenario)[1]
        )

    return mileage_per_vt


# Calculate the annual driver hours.
def calculate_total_driver_hours(
    session, scenario, annual_hours_per_driver=1600, buffer=0.1
):
    # Get the driver hours over the simulation period as the sum of the duration of all driving events.

    driver_hours = datetime.timedelta(seconds=0)
    driving_and_opcharge_events = (
        session.query(Event)
        .filter(
            Event.scenario_id == scenario.id,
            or_(
                Event.event_type == "DRIVING",
                Event.event_type == "CHARGING_OPPORTUNITY",
            ),
        )
        .all()
    )

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
    scenario_params: Optional["ScenarioTCOParameter"] = None,
    vehicle_type_params: Optional[List["VehicleTypeTCOParameter"]] = None,
    battery_type_params: Optional[List["BatteryTypeTCOParameter"]] = None,
    charging_point_type_params: Optional[List["ChargingPointTypeTCOParameter"]] = None,
    charging_infra_params: Optional[List["ChargingInfrastructureTCOParameter"]] = None,
):
    """
    Initialize the TCO parameters for the given scenario in the database.

    All parameter arguments accept dataclass instances from :mod:`eflips.tco.tco_parameter_config`.
    Database IDs are resolved internally by name matching (``name_short`` for vehicle types,
    ``vehicle_name_short`` for battery types, ``type`` for charging points and infrastructure).

    :param scenario: An eflips.model.Scenario object or any object containing a valid scenario id.
    :param database_url: The database URL to connect to.
    :param scenario_params: A :class:`ScenarioTCOParameter` instance.
    :param vehicle_type_params: A list of :class:`VehicleTypeTCOParameter` instances. Matched to
        existing VehicleTypes in the database by ``name_short``.
    :param battery_type_params: A list of :class:`BatteryTypeTCOParameter` instances. Matched via
        ``vehicle_name_short`` to find the associated VehicleType. If the VehicleType has no
        BatteryType, a new one is created using ``specific_mass`` and ``chemistry`` from the
        dataclass.
    :param charging_point_type_params: A list of :class:`ChargingPointTypeTCOParameter` instances.
        Converted via ``to_dict()`` and matched/created by ``type`` ("depot" or "opportunity").
    :param charging_infra_params: A list of :class:`ChargingInfrastructureTCOParameter` instances.
        Converted via ``to_dict()`` and applied to stations by ``type`` ("station" or "depot").
    """

    with create_session(scenario, database_url) as (session, scenario):
        # --- Scenario TCO parameters ---
        if scenario_params is not None:
            scenario.tco_parameters = scenario_params.to_dict()

        # --- Vehicle types: match by name_short ---
        if vehicle_type_params is not None:
            for vt_param in vehicle_type_params:
                vt = (
                    session.query(VehicleType)
                    .filter(
                        VehicleType.name_short == vt_param.name_short,
                        VehicleType.scenario_id == scenario.id,
                    )
                    .one_or_none()
                )

                if vt is None:
                    warnings.warn(
                        f"VehicleType with name_short '{vt_param.name_short}' not found "
                        f"in scenario {scenario.id}. Skipping."
                    )
                    continue

                vt.tco_parameters = vt_param.to_dict(vt.id)

        # --- Battery types: match via vehicle_name_short ---
        if battery_type_params is not None:
            for bt_param in battery_type_params:
                vt = (
                    session.query(VehicleType)
                    .filter(
                        VehicleType.name_short == bt_param.vehicle_name_short,
                        VehicleType.scenario_id == scenario.id,
                    )
                    .one_or_none()
                )

                if vt is None:
                    warnings.warn(
                        f"VehicleType with name_short '{bt_param.vehicle_name_short}' not found "
                        f"in scenario {scenario.id}. Skipping battery '{bt_param.name}'."
                    )
                    continue

                if vt.battery_type_id is not None:
                    # Update existing battery type
                    battery_type = (
                        session.query(BatteryType)
                        .filter(BatteryType.id == vt.battery_type_id)
                        .one()
                    )
                    battery_type.tco_parameters = bt_param.to_dict(battery_type.id)
                else:
                    # Create new battery type. specific_mass and chemistry are taken from the
                    # dataclass defaults — override them in the config if the defaults are not
                    # appropriate for your scenario.
                    new_battery_type = BatteryType(
                        scenario_id=scenario.id,
                        specific_mass=bt_param.specific_mass,
                        chemistry=bt_param.chemistry,
                        tco_parameters=bt_param.to_dict(),
                    )
                    session.add(new_battery_type)
                    vt.battery_type = new_battery_type

        # --- Charging point types: match existing by association, or create new ---
        if charging_point_type_params is not None:
            for cp_param in charging_point_type_params:
                cp_dict = cp_param.to_dict()

                match cp_param.type:
                    case "depot":
                        # Try to find existing ChargingPointTypes linked to Areas.
                        # Currently assumes at most one depot charging point type per scenario.
                        # TODO: support multiple depot charging point types if needed.
                        existing_cps = (
                            session.query(ChargingPointType)
                            .join(Area, Area.charging_point_type_id == ChargingPointType.id)
                            .filter(Area.scenario_id == scenario.id)
                            .distinct()
                            .all()
                        )
                        assert len(existing_cps) <= 1, (
                            f"Expected at most 1 depot ChargingPointType in scenario "
                            f"{scenario.id}, found {len(existing_cps)}."
                        )
                        if existing_cps:
                            existing_cps[0].tco_parameters = cp_dict
                        else:
                            new_cp_type = ChargingPointType(
                                name=cp_param.name,
                                scenario_id=scenario.id,
                                tco_parameters=cp_dict,
                            )
                            session.add(new_cp_type)
                            charging_areas = session.query(Area).filter(
                                Area.processes.any(Process.electric_power.isnot(None)),
                                Area.scenario_id == scenario.id,
                            )
                            for area in charging_areas:
                                area.charging_point_type = new_cp_type

                    case "opportunity":
                        # Try to find existing ChargingPointTypes linked to Stations.
                        # Currently assumes at most one opportunity charging point type per scenario.
                        # TODO: support multiple opportunity charging point types if needed.
                        existing_cps = (
                            session.query(ChargingPointType)
                            .join(Station, Station.charging_point_type_id == ChargingPointType.id)
                            .filter(Station.scenario_id == scenario.id)
                            .distinct()
                            .all()
                        )
                        assert len(existing_cps) <= 1, (
                            f"Expected at most 1 opportunity ChargingPointType in scenario "
                            f"{scenario.id}, found {len(existing_cps)}."
                        )
                        if existing_cps:
                            existing_cps[0].tco_parameters = cp_dict
                        else:
                            new_cp_type = ChargingPointType(
                                name=cp_param.name,
                                scenario_id=scenario.id,
                                tco_parameters=cp_dict,
                            )
                            session.add(new_cp_type)
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
                                station.charging_point_type = new_cp_type

                    case _:
                        raise ValueError(
                            f"Unknown charging point type: {cp_param.type}"
                        )

        # --- Charging infrastructure: convert to dict, same matching logic ---
        if charging_infra_params is not None:
            for infra_param in charging_infra_params:
                infra_dict = infra_param.to_dict()

                match infra_dict.get("type"):
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
                            station.tco_parameters = infra_dict
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
                            station.tco_parameters = infra_dict
                    case _:
                        raise ValueError(
                            f"Unknown infrastructure type: {infra_dict.get('type')}"
                        )

        session.commit()

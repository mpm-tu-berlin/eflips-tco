import os
from datetime import datetime, timedelta, timezone

import eflips.model
import pytest
from eflips.model import (
    Area,
    AreaType,
    AssocPlanProcess,
    AssocRouteStation,
    Base,
    BatteryType,
    Depot,
    Line,
    Plan,
    Process,
    Rotation,
    Route,
    Scenario,
    Station,
    StopTime,
    Trip,
    TripType,
    Vehicle,
    VehicleClass,
    VehicleType,
    ChargingPointType,
    VoltageLevel,
    ChargeType,
    Event,
    EventType,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eflips.depot.api import simulate_scenario, simple_consumption_simulation
from eflips.tco import TCOCalculator


class TestHelpers:
    @pytest.fixture()
    def scenario(self, session):
        """
        Creates a scenario.

        :param session: An SQLAlchemy Session with the eflips-model schema
        :return: A :class:`Scenario` object
        """
        scenario = Scenario(name="Test Scenario")
        session.add(scenario)
        session.commit()
        return scenario

    @pytest.fixture()
    def full_scenario(self, session):
        """
        Creates a scenario that comes filled with sample content for each type.

        :param session: An SQLAlchemy Session with the eflips-model schema
        :return: A :class:`Scenario` object
        """

        # Add a scenario
        scenario = Scenario(name="Test Scenario")
        session.add(scenario)

        # Add a vehicle type with a battery type
        vehicle_type = VehicleType(
            scenario=scenario,
            name="Test Vehicle Type",
            battery_capacity=100,
            charging_curve=[[0, 150], [1, 150]],
            opportunity_charging_capable=True,
            length=10,
            width=2.5,
            height=4,
        )
        session.add(vehicle_type)
        battery_type = BatteryType(
            scenario=scenario, specific_mass=100, chemistry={"test": "test"}
        )
        session.add(battery_type)
        vehicle_type.battery_type = battery_type

        # Add a vehicle type without a battery type
        vehicle_type = VehicleType(
            scenario=scenario,
            name="Test Vehicle Type 2",
            battery_capacity=100,
            charging_curve=[[0, 150], [1, 150]],
            opportunity_charging_capable=True,
            length=10,
            width=2.5,
            height=4,
        )
        session.add(vehicle_type)

        # Add a VehicleClass
        vehicle_class = VehicleClass(
            scenario=scenario,
            name="Test Vehicle Class",
            vehicle_types=[vehicle_type],
        )
        session.add(vehicle_class)

        line = Line(
            scenario=scenario,
            name="Test Line",
            name_short="TL",
        )
        session.add(line)

        stop_1 = Station(
            scenario=scenario,
            name="Test Station 1",
            name_short="TS1",
            geom="POINT(0 0 0)",
            is_electrified=False,
        )
        session.add(stop_1)

        stop_2 = Station(
            scenario=scenario,
            name="Test Station 2",
            name_short="TS2",
            geom="POINT(1 0 0)",
            is_electrified=False,
        )
        session.add(stop_2)

        stop_3 = Station(
            scenario=scenario,
            name="Test Station 3",
            name_short="TS3",
            geom="POINT(2 0 0)",
            is_electrified=True,
            charge_type=ChargeType.OPPORTUNITY,
            power_total=150,
            power_per_charger=150,
            voltage_level=VoltageLevel.MV,
            amount_charging_places=1,
        )

        route_1 = Route(
            scenario=scenario,
            name="Test Route 1",
            name_short="TR1",
            departure_station=stop_1,
            arrival_station=stop_3,
            line=line,
            distance=1000,
        )
        assocs = [
            AssocRouteStation(
                scenario=scenario, station=stop_1, route=route_1, elapsed_distance=0
            ),
            AssocRouteStation(
                scenario=scenario, station=stop_2, route=route_1, elapsed_distance=500
            ),
            AssocRouteStation(
                scenario=scenario, station=stop_3, route=route_1, elapsed_distance=1000
            ),
        ]
        route_1.assoc_route_stations = assocs
        session.add(route_1)

        route_2 = Route(
            scenario=scenario,
            name="Test Route 2",
            name_short="TR2",
            departure_station=stop_3,
            arrival_station=stop_1,
            line=line,
            distance=1000,
        )
        assocs = [
            AssocRouteStation(
                scenario=scenario, station=stop_3, route=route_2, elapsed_distance=0
            ),
            AssocRouteStation(
                scenario=scenario, station=stop_2, route=route_2, elapsed_distance=100
            ),
            AssocRouteStation(
                scenario=scenario, station=stop_1, route=route_2, elapsed_distance=1000
            ),
        ]
        route_2.assoc_route_stations = assocs
        session.add(route_2)

        # Add the schedule objects
        first_departure = datetime(
            year=2020, month=1, day=1, hour=12, minute=0, second=0, tzinfo=timezone.utc
        )
        interval = timedelta(minutes=30)
        duration = timedelta(minutes=20)

        # Create a number of rotations
        number_of_rotations = 3
        for rotation_id in range(number_of_rotations):
            trips = []

            rotation = Rotation(
                scenario=scenario,
                trips=trips,
                vehicle_type=vehicle_type,
                allow_opportunity_charging=True,
            )
            session.add(rotation)

            for i in range(15):
                # forward
                trips.append(
                    Trip(
                        scenario=scenario,
                        route=route_1,
                        trip_type=TripType.PASSENGER,
                        departure_time=first_departure + 2 * i * interval,
                        arrival_time=first_departure + 2 * i * interval + duration,
                        rotation=rotation,
                    )
                )
                stop_times = [
                    StopTime(
                        scenario=scenario,
                        station=stop_1,
                        arrival_time=first_departure + 2 * i * interval,
                    ),
                    StopTime(
                        scenario=scenario,
                        station=stop_2,
                        arrival_time=first_departure
                        + 2 * i * interval
                        + timedelta(minutes=5),
                        dwell_duration=timedelta(minutes=1),
                    ),
                    StopTime(
                        scenario=scenario,
                        station=stop_3,
                        arrival_time=first_departure + 2 * i * interval + duration,
                    ),
                ]
                trips[-1].stop_times = stop_times

                # backward
                trips.append(
                    Trip(
                        scenario=scenario,
                        route=route_2,
                        trip_type=TripType.PASSENGER,
                        departure_time=first_departure + (2 * i + 1) * interval,
                        arrival_time=first_departure
                        + (2 * i + 1) * interval
                        + duration,
                        rotation=rotation,
                    )
                )
                stop_times = [
                    StopTime(
                        scenario=scenario,
                        station=stop_3,
                        arrival_time=first_departure + (2 * i + 1) * interval,
                    ),
                    StopTime(
                        scenario=scenario,
                        station=stop_2,
                        arrival_time=first_departure
                        + (2 * i + 1) * interval
                        + timedelta(minutes=5),
                    ),
                    StopTime(
                        scenario=scenario,
                        station=stop_1,
                        arrival_time=first_departure
                        + (2 * i + 1) * interval
                        + duration,
                    ),
                ]
                trips[-1].stop_times = stop_times
            session.add_all(trips)

            first_departure += timedelta(minutes=20)

        # Create a simple depot
        depot = Depot(
            scenario=scenario, name="Test Depot", name_short="TD", station=stop_1
        )
        session.add(depot)

        # Create plan

        plan = Plan(scenario=scenario, name="Test Plan")
        session.add(plan)

        depot.default_plan = plan

        # Create areas
        arrival_area = Area(
            scenario=scenario,
            name="Arrival",
            depot=depot,
            area_type=AreaType.DIRECT_ONESIDE,
            capacity=number_of_rotations + 2,
        )
        session.add(arrival_area)

        cleaning_area = Area(
            scenario=scenario,
            name="Cleaning Area",
            depot=depot,
            area_type=AreaType.DIRECT_ONESIDE,
            capacity=1,
        )
        session.add(cleaning_area)
        cleaning_area.vehicle_type = vehicle_type

        charging_area = Area(
            scenario=scenario,
            name="Line Charging Area",
            depot=depot,
            area_type=AreaType.LINE,
            capacity=24,
            row_count=4,
        )
        session.add(charging_area)
        charging_area.vehicle_type = vehicle_type

        # Create processes
        clean = Process(
            name="Arrival Cleaning",
            scenario=scenario,
            dispatchable=False,
            duration=timedelta(minutes=30),
        )

        charging = Process(
            name="Charging",
            scenario=scenario,
            dispatchable=False,
            electric_power=50,
        )

        standby_departure = Process(
            name="Standby Pre-departure",
            scenario=scenario,
            dispatchable=True,
        )

        session.add(clean)
        session.add(charging)
        session.add(standby_departure)

        cleaning_area.processes.append(clean)
        charging_area.processes.append(charging)
        charging_area.processes.append(standby_departure)

        assocs = [
            AssocPlanProcess(scenario=scenario, process=clean, plan=plan, ordinal=0),
            AssocPlanProcess(scenario=scenario, process=charging, plan=plan, ordinal=1),
            AssocPlanProcess(
                scenario=scenario, process=standby_departure, plan=plan, ordinal=2
            ),
        ]
        session.add_all(assocs)

        for vehicle_type in scenario.vehicle_types:
            vehicle_type.consumption = 1
        session.flush()

        simple_consumption_simulation(scenario, initialize_vehicles=True)
        simulate_scenario(scenario)


        simple_consumption_simulation(scenario, initialize_vehicles=False)

        session.commit()

        return scenario

    @pytest.fixture()
    def tco_parameters(self, session):
        """
        Returns the TCO parameters for the scenario.

        :param session: An SQLAlchemy Session with the eflips-model schema
        :return: A dictionary with TCO parameters
        """
        vehicle_types = [
            {
                "id": 1,
                "name": "Test Vehicle Type 1",
                "useful_life": 14,
                "procurement_cost": 340000.0,
                "cost_escalation": 0.02,
            },
            {
                "id": 2,
                "name": "Test Vehicle Type 2",
                "useful_life": 14,
                "procurement_cost": 603000.0,
                "cost_escalation": 0.02,
            },
        ]

        battery_types = [
            {
                "name": "Test Battery Type 1",
                "procurement_cost": 315,
                "useful_life": 7,
                "cost_escalation": -0.03,
                "vehicle_type_ids": [1, 2],
            },
        ]
        charging_point_types = [
            {
                "type": "depot",
                "name": "Depot Charging Point",
                "procurement_cost": 100000.0,
                "useful_life": 20,
                "cost_escalation": 0.02,
            },
            {
                "type": "opportunity",
                "name": "Opportunity Charging Point",
                "procurement_cost": 275000.0,
                "useful_life": 20,
                "cost_escalation": 0.02,
            },
        ]

        charging_infrastructure = [
            {
                "type": "depot",
                "name": "Depot Charging Infrastructure",
                "procurement_cost": 3400000.0,
                "useful_life": 20,
                "cost_escalation": 0.02,
            },
            {
                "type": "station",
                "name": "Opportunity Charging Infrastructure",
                "procurement_cost": 500000.0,
                "useful_life": 20,
                "cost_escalation": 0.02,
            },
        ]

        scenario_tco_parameters = {
            "project_duration": 20,
            "interest_rate": 0.04,
            "inflation_rate": 0.02,
            "staff_cost": 25.0,  # calculated: 35,000 € p.a. per driver/1600 h p.a. per driver
            # Fuel cost in EUR per unit fuel
            "fuel_cost": 0.1794,  # electricity cost
            # Maintenance cost in EUR per km
            "maint_cost": 0.35,
            # Maintenance cost infrastructure per year and charging slot
            "maint_infr_cost": 1000,
            # Taxes and insurance cost in EUR per year and bus
            "taxes": 278,
            "insurance": 9693,  # DCO #9703, # EBU
            # Cost escalation factors (cef / pef)
            "pef_general": 0.02,
            "pef_wages": 0.025,
            "pef_fuel": 0.038,
            "pef_insurance": 0.02,
        }

        return {
            "vehicle_types": vehicle_types,
            "battery_types": battery_types,
            "charging_point_types": charging_point_types,
            "charging_infrastructure": charging_infrastructure,
            "scenario_tco_parameters": scenario_tco_parameters,
        }

    @pytest.fixture()
    def session(self):
        """
        Creates a session with the eflips-model schema.

        NOTE: THIS DELETE ALL DATA IN THE DATABASE
        :return: an SQLAlchemy Session with the eflips-model schema
        """
        url = os.environ["DATABASE_URL"]
        engine = create_engine(
            url, echo=False
        )  # Change echo to True to see SQL queries
        Base.metadata.drop_all(engine)
        eflips.model.setup_database(engine)
        session = Session(bind=engine)
        yield session
        session.close()


class TestApi(TestHelpers):
    """
    Tests the API of the eflips-tco package.
    """

    def test_tco_calculation_with_scenario(self, session, full_scenario, tco_parameters):
        """
        Tests the initialization of TCO parameters.
        """


        tco_calculator = TCOCalculator(scenario=full_scenario, tco_parameters=tco_parameters)



        tco_keys = ["name", "useful_life", "procurement_cost", "cost_escalation"]

        def check_tco_parameters(obj, tco_keys):

            tco_parameters = obj.tco_parameters
            assert tco_parameters is not None
            assert isinstance(tco_parameters, dict)
            for key in tco_keys:
                assert key in tco_parameters
                assert isinstance(tco_parameters[key], (int, float, str))

        vehicles_and_battery_types = (
            session.query(
                VehicleType,
                BatteryType,
            )
            .join(BatteryType, BatteryType.id == VehicleType.battery_type_id)
            .join(Vehicle, Vehicle.vehicle_type_id == VehicleType.id)
            .filter(VehicleType.scenario_id == full_scenario.id)
            .group_by(VehicleType.id, VehicleType.battery_capacity, BatteryType.id)
            .all()
        )
        assert len(vehicles_and_battery_types) > 0

        for vt, bt in vehicles_and_battery_types:

            check_tco_parameters(vt, tco_keys)
            check_tco_parameters(bt, tco_keys)

        charging_points_used_depot = (
            session.query(ChargingPointType)
            .join(Area, Area.charging_point_type_id == ChargingPointType.id)
            .filter(Area.scenario_id == full_scenario.id)
            .all()
        )
        assert len(charging_points_used_depot) > 0
        for cpt in charging_points_used_depot:
            check_tco_parameters(cpt, tco_keys)

        charging_points_used_station = (
            session.query(ChargingPointType)
            .join(Station, Station.charging_point_type_id == ChargingPointType.id)
            .filter(Station.scenario_id == full_scenario.id)
            .all()
        )
        assert len(charging_points_used_station) > 0
        for cpt in charging_points_used_station:
            check_tco_parameters(cpt, tco_keys)

        depot_stations = (
            session.query(Station)
            .join(Depot, Depot.station_id == Station.id)
            .filter(Station.scenario_id == full_scenario.id)
            .all()
        )

        assert len(depot_stations) > 0
        for depot_station in depot_stations:
            check_tco_parameters(depot_station, tco_keys)

        oppo_stations = (
            session.query(Station)
            .join(Event, Event.station_id == Station.id)
            .filter(Event.event_type == EventType.CHARGING_OPPORTUNITY)
            .filter(Station.scenario_id == full_scenario.id)
            .all()
        )

        assert len(oppo_stations) > 0
        for oppo_station in oppo_stations:
            check_tco_parameters(oppo_station, tco_keys)

        tco_calculator.calculate()
        assert isinstance(tco_calculator.tco_per_distance, float)
        assert tco_calculator.tco_per_distance >= 0.0

    def test_tco_calculation_with_id(self, session, full_scenario,tco_parameters):

        tco_calculator = TCOCalculator(scenario=full_scenario.id, database_url=os.environ["DATABASE_URL"],
                                       tco_parameters=tco_parameters)

        tco_keys = ["name", "useful_life", "procurement_cost", "cost_escalation"]

        def check_tco_parameters(obj, tco_keys):

            tco_parameters = obj.tco_parameters
            assert tco_parameters is not None
            assert isinstance(tco_parameters, dict)
            for key in tco_keys:
                assert key in tco_parameters
                assert isinstance(tco_parameters[key], (int, float, str))

        vehicles_and_battery_types = (
            session.query(
                VehicleType,
                BatteryType,
            )
            .join(BatteryType, BatteryType.id == VehicleType.battery_type_id)
            .join(Vehicle, Vehicle.vehicle_type_id == VehicleType.id)
            .filter(VehicleType.scenario_id == full_scenario.id)
            .group_by(VehicleType.id, VehicleType.battery_capacity, BatteryType.id)
            .all()
        )
        assert len(vehicles_and_battery_types) > 0

        for vt, bt in vehicles_and_battery_types:
            check_tco_parameters(vt, tco_keys)
            check_tco_parameters(bt, tco_keys)

        charging_points_used_depot = (
            session.query(ChargingPointType)
            .join(Area, Area.charging_point_type_id == ChargingPointType.id)
            .filter(Area.scenario_id == full_scenario.id)
            .all()
        )
        assert len(charging_points_used_depot) > 0
        for cpt in charging_points_used_depot:
            check_tco_parameters(cpt, tco_keys)

        charging_points_used_station = (
            session.query(ChargingPointType)
            .join(Station, Station.charging_point_type_id == ChargingPointType.id)
            .filter(Station.scenario_id == full_scenario.id)
            .all()
        )
        assert len(charging_points_used_station) > 0
        for cpt in charging_points_used_station:
            check_tco_parameters(cpt, tco_keys)

        depot_stations = (
            session.query(Station)
            .join(Depot, Depot.station_id == Station.id)
            .filter(Station.scenario_id == full_scenario.id)
            .all()
        )

        assert len(depot_stations) > 0
        for depot_station in depot_stations:
            check_tco_parameters(depot_station, tco_keys)

        oppo_stations = (
            session.query(Station)
            .join(Event, Event.station_id == Station.id)
            .filter(Event.event_type == EventType.CHARGING_OPPORTUNITY)
            .filter(Station.scenario_id == full_scenario.id)
            .all()
        )

        assert len(oppo_stations) > 0
        for oppo_station in oppo_stations:
            check_tco_parameters(oppo_station, tco_keys)

        tco_calculator.calculate()
        assert isinstance(tco_calculator.tco_per_distance, float)
        assert tco_calculator.tco_per_distance >= 0.0


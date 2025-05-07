import os


from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sqlalchemy import and_


import eflips.model
from eflips.model import (
    Area,
    BatteryType,
    Process,
    Scenario,
    Station,
    VehicleType,
    ChargingPointType,
)

# This script adds TCO parameters to vehicle types and stations in the database. If all parameters are correctly set,
# we only need to run this once.


if __name__ == "__main__":
    engine = create_engine(
        os.environ["DATABASE_URL"], echo=False
    )  # Change echo to True to see SQL queries

    # Create a session with the eflips-model schema

    eflips.model.setup_database(engine)

    session = Session(engine)

    scenarios = session.query(Scenario).all()
    for scenario in scenarios:
        print(f"Scenario ID: {scenario.id}, Name: {scenario.name}")

        # Add tco parameters to vehicle types
        vehicle_types = session.query(VehicleType).filter(VehicleType.scenario == scenario).all()


        for vehicle_type in vehicle_types:
            # Add battery types. We can assume that each vehicle type has a unique battery type.

            # An example battery type

            match vehicle_type.name:
                case "Ebusco 3.0 12 large battery":
                    battery_type = BatteryType(
                        scenario=scenario,
                        specific_mass=5.0,
                        chemistry={"Test": "Test"},
                        tco_parameters={
                            "procurement_cost": 350.0,
                            "lifetime": 6,
                            "cost_escalation": -0.03
                        }
                    )
                    session.add(battery_type)
                    vehicle_type.tco_parameters = {
                        "procurement_cost": 370000.0,
                        "lifetime": 12,
                        "cost_escalation": 0.025
                    }
                    vehicle_type.battery_type = battery_type

                case "Solaris Urbino 18 large battery":

                    # TODO list all cases like this and add the parameters

                    raise NotImplementedError

                case _:
                    raise ValueError(
                        f"Vehicle type {vehicle_type.name} not recognized. Please add the parameters manually.")

        # Add tco parameters for all stations

        stations = session.query(Station).filter(Station.scenario == scenario).all()

        for station in stations:
            if station.depot is None:
                # a charging station
                charging_point_type_station = ChargingPointType(
                    scenario=scenario,
                    name="Charging Point Type Station",
                    tco_parameters={
                        "procurement_cost": 275000.0,
                        "lifetime": 12,
                        "cost_escalation": 0.02
                    }
                )
                session.add(charging_point_type_station)

                station.tco_parameters = {
                    "procurement_cost": 3400000.0,
                    "lifetime": 12,
                    "cost_escalation": 0.02
                    }
            else:
                # A depot.
                station.tco_parameters = {
                    "procurement_cost": 500000.0,
                    "lifetime": 12,
                    "cost_escalation": 0.02
                }
                station.charging_point_type = charging_point_type_station

        # Add tco parameters for charging areas in depots

        charging_point_type_depot = ChargingPointType(
            scenario=scenario,
            name="Charging Point Type Depot",
            tco_parameters={
                "procurement_cost": 100000.0,
                "lifetime": 12,
                "cost_escalation": 0.02
            }
        )
        session.add(charging_point_type_depot)

        charging_areas = (
            session.query(Area)
            .filter(
                Area.scenario_id == scenario.id,
                Area.processes.any(
                    and_(
                        Process.electric_power.isnot(None),
                        Process.duration.is_(None),
                    )
                ),
            )
            .all()
        )

        for area in charging_areas:
            area.charging_point_type = charging_point_type_depot

    session.commit()
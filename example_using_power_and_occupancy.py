import os


from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sqlalchemy import and_

from eflips.eval.output.prepare import power_and_occupancy

import eflips.model
from eflips.model import (
    Area,
    Station,
    Process,
    Scenario,
)

# This script shows the usage of the power_and_occupancy function to get the number of slots in depots and in stations.
if __name__ == "__main__":
    engine = create_engine(os.environ["DATABASE_URL"], echo=False)  # Change echo to True to see SQL queries

    # Create a session with the eflips-model schema

    eflips.model.setup_database(engine)


    session = Session(engine)

    # Example scenario

    scenario = session.query(Scenario).filter(Scenario.id == 4).first()

    # Example area

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

    example_area = charging_areas[0]  # Example area

    # Charging point number of this area. We can also pass a list of areas, which will return the occupancy of these
    # areas alltogeter.
    num_charging_point = power_and_occupancy(example_area.id, session)["occupancy_charging"].max()

    print(f"Number of charging points: {num_charging_point}")

    # You can calculate the total cost of charging point in this area like this, after tco_parameters are set
    # print(example_area.charging_point_type.tco_parameters["procurement_cost"] * num_charging_point)


    example_station = session.query(Station).filter(Station.id == 103262862).first()
    num_station_charging_point = power_and_occupancy(area_id=None, session=session, station_id=example_station.id)["occupancy_charging"].max()
    print(f"Number of charging points: {num_station_charging_point}")
    # print(example_station.charging_point_type.tco_parameters["procurement_cost"] * num_station_charging_point)
from typing import Union


from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from eflips.model import Scenario

from eflips.tco.data_queries import get_capex_input_dict, get_opex_input_dict, get_passenger_mileage, get_total_fleet_mileage
#TODO rename the file tco_utils.py
from eflips.tco.tco_utils import tco_calculation

import parameters as p
def calculate_tco(scenario: Union[Scenario, int], database_url):
    """

    Calculate the Total Cost of Ownership (TCO) for a given scenario.
    :param scenario:
    :param database_url:
    :return:
    """

    # create session
    engine = create_engine(database_url)
    with Session(engine) as session:

        # Check if scenario exists
        if isinstance(scenario, int):
            scenario = session.query(Scenario).filter(Scenario.id == scenario).one()
        if not scenario:
            raise ValueError("Scenario does not exist in the database.")

        capex_dict = get_capex_input_dict(session, scenario)

        opex_dict = get_opex_input_dict(session, scenario)

        passenger_mileage = get_passenger_mileage(session, scenario)
        annual_fleet_mileage = get_total_fleet_mileage(session, scenario)

        session.close()


    # Calculate annual fleet mileage

    tco_input_dict = {
        "project_duration": p.project_duration,
        "interest_rate": p.interest_rate,
        "discount_rate": p.inflation_rate,
        "scenario": scenario.id,
        "passenger_mileage": passenger_mileage,
        "annual_fleet_mileage": annual_fleet_mileage
    }

    tco_result = tco_calculation(capex_dict, opex_dict,tco_input_dict, True)

    # TCO over project duration
    tco_pd = tco_result["TCO_over_PD"]

    # Annual TCO
    tco_ann = tco_pd / p.project_duration

    # Specific TCO over project duration
    tco_sp_pd = tco_pd / (annual_fleet_mileage * p.project_duration)

    return tco_ann, tco_sp_pd























        # Get data from database
        # - input dict capex
        # - input dict opex

    # Close session



    # calculate tco

    # return result and save figures. How?


    raise NotImplementedError



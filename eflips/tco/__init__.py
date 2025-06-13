# from typing import Union
#
# from sqlalchemy.orm import Session
# from sqlalchemy import create_engine, func
# from eflips.model import Scenario, Route, Trip
#
# from eflips.tco.data_queries import (
#     get_capex_input,
#     get_opex_input,
#     get_simulation_period,
# )
#
# # TODO rename the file tco_utils.py
# from eflips.tco.tco_utils import tco_calculation, CapexItem, AssetType
# from eflips.tco.data_queries import get_fleet_mileage_by_vehicle_type
#
# import parameters as p
#
#
#
#
#
#
# def calculate_tco(scenario: Union[Scenario, int], database_url):
#     """
#
#     Calculate the Total Cost of Ownership (TCO) for a given scenario.
#     :param scenario:
#     :param database_url:
#     :return:
#     """
#
#     # create session
#     engine = create_engine(database_url)
#     with Session(engine) as session:
#
#         # TODO consider taking those out because calculate_tco and tco_calculation later are bad naming
#
#         # Check if scenario exists
#         if isinstance(scenario, int):
#             scenario = session.query(Scenario).filter(Scenario.id == scenario).one()
#         if not scenario:
#             raise ValueError("Scenario does not exist in the database.")
#
#         capex_input = get_capex_input(session, scenario)
#
#         opex_input = get_opex_input(session, scenario, capex_input)
#
#         passenger_mileage = (
#             session.query(func.sum(Route.distance))
#             .join(Trip, Route.id == Trip.route_id)
#             .filter(Trip.scenario_id == scenario.id, Trip.trip_type == "PASSENGER")
#             .one()[0]
#             * get_simulation_period(session, scenario)[1]
#             / 1000
#         )
#
#         # annual_fleet_mileage = sum(
#         #     asset.annual_mileage for asset in capex_input if asset.asset_type == AssetType.VEHICLE)
#
#         annual_fleet_mileage = sum(
#             vt_mileage
#             for vt, vt_mileage in get_fleet_mileage_by_vehicle_type(
#                 session, scenario
#             ).items()
#         )
#         session.close()
#
#     # Calculate annual fleet mileage
#
#     # TODO might move project_duration, inflation_rate and interest_rate to the scenario object
#
#     tco_input_dict = {
#         "project_duration": p.project_duration,
#         "interest_rate": p.interest_rate,
#         "discount_rate": p.inflation_rate,
#         "scenario": scenario.id,
#         "passenger_mileage": passenger_mileage,
#         "annual_fleet_mileage": annual_fleet_mileage,
#     }
#
#     tco_result = tco_calculation(capex_input, opex_input, tco_input_dict, True)
#
#     # TCO over project duration
#     tco_pd = tco_result["TCO_over_PD"]
#
#     # Annual TCO
#     tco_ann = tco_pd / p.project_duration
#
#     # Specific TCO over project duration
#     tco_sp_pd = tco_pd / (annual_fleet_mileage * p.project_duration)
#
#     return tco_ann, tco_sp_pd
#
#     # Get data from database
#     # - input dict capex
#     # - input dict opex
#
#     # Close session
#
#     # calculate tco
#
#     # return result and save figures. How?
#
#     raise NotImplementedError

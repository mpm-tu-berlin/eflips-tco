from eflips.model import (Scenario, VehicleType, BatteryType, ChargingPointType,
                          Route, Trip, Vehicle, Area, Depot, Station, Event)

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func

from eflips.tco.data_queries import (load_capex_items_vehicle,
                                     load_capex_items_battery,
                                     load_capex_items_infrastructure,
                                     get_annual_fleet_mileage,
                                     calculate_total_driver_hours,
                                     get_total_energy_consumption)

from eflips.tco.tco_utils import (replacement_cost, annuity, net_present_value)
from eflips.tco.cost_items import CapexItem, OpexItem, CapexItemType

import pandas as pd




class TCOCalculator:
    """
    This class is used to calculate the total cost of ownership based on the input data provided in the dictionaries.
    It contains methods to calculate the CAPEX and OPEX sections of the TCO.
    """

    def __init__(self, scenario_id, database_url, capex_items=None, opex_items=None):
        """

        :param scenario:
        :param database_url:
        """
        # create session
        session = Session(create_engine(database_url))
        with session:
            self.scenario = session.query(Scenario).filter(Scenario.id == scenario_id).one()

            annual_fleet_mileage = get_annual_fleet_mileage(session, self.scenario)
            self.annual_fleet_mileage = annual_fleet_mileage

            if capex_items is None:
                try:
                    self._load_capex_items_from_db(session)
                except Exception as e:
                    raise ValueError(
                        "Error loading CAPEX items from the database. Please make sure the tco-related data exists in "
                        "the database, or use your own list of capex items."
                    ) from e
            else:
                self.capex_items = capex_items

            if opex_items is None:
                try:
                    self.opex_items = self._load_opex_items_from_db(session, self.capex_items, annual_fleet_mileage)
                except Exception as e:
                    # raise ValueError(
                    #     "Error loading OPEX items from the database. Please make sure the tco-related data exists in "
                    #     "the database, or use your own list of opex items."
                    # ) from e
                    raise e
            else:
                self.opex_items = opex_items

            # initialize scenario related data
            # TODO get this from the scenario
            self.project_duration = 12
            self.interest_rate = 0.04
            self.inflation_rate = 0.025

            # Initialize the output values
            self.total_capex = 0
            self.total_opex = 0
            self.tco_over_project_duration = 0
            self.tco_per_distance = 0  # TODO better name?
            self.tco_by_type = {}

        session.close()

    def calculate(self):
        """
        Calculate the total cost of ownership based on the input data provided in the dictionaries.
        :return: A dictionary containing the TCO results.
        """

        # ----------Total CAPEX----------#

        # Calculate the total cost for each asset over the project duration.
        for capex_item in self.capex_items:
            # Calculate the procurement cost for the respective asset including replacement.
            # TODO general_input_dict can be replaced after adding tco parameters to the scenario object.
            procurement_this_type = capex_item.calculate_total_procurement_cost(
                project_duration=self.project_duration,
                interest_rate=self.interest_rate,
                net_discount_rate=self.inflation_rate,
            ) * capex_item.quantity
            # Add the cost of this asset to the CAPEX section of the TCO.

            self.tco_by_type[capex_item.name] = procurement_this_type
            self.total_capex += procurement_this_type

        # ----------Total OPEX----------#

        # Calculate the OPEX for each category over the whole project duration.
        for opex_item in self.opex_items:

            total_opex_of_type = 0

            # Calculate the OPEX for each year.
            for year in range(self.project_duration):
                opex_cost_in_respective_year = opex_item.future_cost(year)
                total_opex_of_type += net_present_value(
                    opex_cost_in_respective_year, year, self.inflation_rate
                )

            self.tco_by_type[opex_item.name] = total_opex_of_type

            self.total_opex += total_opex_of_type

        # ----------Calculation of three kinds of TCO----------#

        # TCO over project duration
        self.tco_over_project_duration = self.total_opex + self.total_capex

        # Annual TCO
        # TODO do we need this? maybe later

        # Specific TCO over project duration
        self.tco_per_distance = self.tco_over_project_duration / self.annual_fleet_mileage

        dict_tco_by_type = self.tco_by_type
        self.tco_by_type = pd.DataFrame.from_dict(
            dict_tco_by_type, orient="index", columns=["Cost"]
        ).reset_index()
        # divide the costs by the annual fleet mileage to get the specific costs
        self.tco_by_type["Specific Cost"] = (
            self.tco_by_type["Cost"] / self.annual_fleet_mileage
        )



    def visualize(self):
        """
        Visualize the TCO results.
        :return: A dictionary containing the TCO results.
        """
        # TODO implement this method
        raise NotImplementedError("This method is not implemented yet.")

    def _load_capex_items_from_db(self, session):
        # Get the number of vehicles used in the simulation by vehicle type including the tco parameters.
        assets_vehicle = load_capex_items_vehicle(session, self.scenario)

        # Get the battery size by bus type including the tco parameters
        assets_battery = load_capex_items_battery(session, self.scenario)

        # Get the number of charging infrastructure and slots by type. There are only depot or
        # terminal stop (opportunity) charging stations.
        assets_infrastructure = load_capex_items_infrastructure(session, self.scenario)

        capex_items = (
                list(assets_vehicle) + list(assets_battery) + list(assets_infrastructure)
        )
        self.capex_items = capex_items

    def _load_opex_items_from_db(self, session, capex_input, annual_fleet_mileage):
        """
            This method returns the opex input dictionary, which is used to calculate the TCO.
            :return: A dictionary including the opex input data.
            """

        list_opex_items = []

        # TODO this is a temporary solution, it should be replaced by adding tco parameters into the scenario

        # Uncomment this when tco parameters are added to the scenario
        # scenario_tco_parameters = scenario.tco_parameters
        scenario_tco_parameters = {
            # hourly staff cost in EUR per driver
            "staff_cost": 21.875,  # calculated: 35,000 € p.a. per driver/1600 h p.a. per driver
            "annual_staff_cost": 35000,

            # Fuel cost in EUR per unit fuel
            "fuel_cost": 0.1794,  # electricity cost

            # Maintenance cost in EUR per km
            "maint_cost": 0.35,

            # Maintenance cost infrastructure per year and charging slot
            "maint_infr_cost": 1000,

            # Taxes and insurance cost in EUR per year and bus
            "taxes": 400.50,
            "insurance": 300,

            # Cost escalation factors (cef / pef)
            "pef_general": 0.02,
            "pef_wages": 0.02,
            "pef_fuel": 0.038,
            "pef_insurance": 0.1,
        }

        # Get the annual driver hours

        # TODO should we avoid using OpexItem here?

        total_driver_hours = calculate_total_driver_hours(session, self.scenario)
        staff_cost = OpexItem(
            name="Staff Cost",
            unit_cost=scenario_tco_parameters["staff_cost"],
            usage_amount=total_driver_hours,
            cost_escalation=scenario_tco_parameters["pef_wages"],
        )
        list_opex_items.append(staff_cost)

        # Get the total energy consumption
        total_energy_consumption = get_total_energy_consumption(session, self.scenario)
        # TODO maybe change it to energy_cost
        fuel_cost = OpexItem(
            name="Fuel Cost",
            unit_cost=scenario_tco_parameters["fuel_cost"],
            usage_amount=total_energy_consumption,
            cost_escalation=scenario_tco_parameters["pef_fuel"],
        )
        list_opex_items.append(fuel_cost)

        # Get the total fleet mileage

        maint_cost_vehicles = OpexItem(
            name="Maintenance Cost Vehicles",
            unit_cost=scenario_tco_parameters["maint_cost"],
            usage_amount=annual_fleet_mileage,
            cost_escalation=scenario_tco_parameters["pef_general"],
        )
        list_opex_items.append(maint_cost_vehicles)

        total_number_vehicles = sum(
            asset.quantity for asset in capex_input if asset.asset_type == CapexItemType.VEHICLE
        )
        insurance = OpexItem(
            name="Insurance",
            unit_cost=scenario_tco_parameters["insurance"],
            usage_amount=total_number_vehicles,
            cost_escalation=scenario_tco_parameters["pef_insurance"],
        )
        list_opex_items.append(insurance)

        taxes = OpexItem(
            name="Taxes",
            unit_cost=scenario_tco_parameters["taxes"],
            usage_amount=total_number_vehicles,
            cost_escalation=scenario_tco_parameters["pef_general"],
        )
        list_opex_items.append(taxes)

        total_number_charging_points = sum(
            asset.quantity
            for asset in capex_input
            if asset.asset_type == CapexItemType.INFRASTRUCTURE
        )
        maint_cost_infra = OpexItem(
            name="Maintenance Cost Infrastructure",
            unit_cost=scenario_tco_parameters["maint_infr_cost"],
            usage_amount=total_number_charging_points,
            cost_escalation=scenario_tco_parameters["pef_general"],
        )
        list_opex_items.append(maint_cost_infra)

        return list_opex_items

from eflips.model import (
    Scenario, Trip, Rotation,
)

from typing import Optional

from eflips.tco.data_queries import (
    load_capex_items_vehicle,
    load_capex_items_battery,
    load_capex_items_infrastructure,
    get_annual_fleet_mileage,
    calculate_total_driver_hours,
    calc_energy_consumption_simulated,
    get_mileage_per_vehicle_type,
)

from eflips.tco.cost_items import CapexItem, OpexItem, CapexItemType, OpexItemType, net_present_value
from eflips.tco.util import create_session

import pandas as pd


class TCOCalculator:
    """
    This class is used to calculate the total cost of ownership based on the input data provided in the dictionaries.
    It contains methods to calculate the CAPEX and OPEX sections of the TCO.
    """

    def __init__(self, scenario, database_url: Optional[str] = None, energy_consumption_mode="simulated", capex_items=None, opex_items=None):
        """

        :param scenario:
        :param database_url:
        """
        # create session
        with create_session(scenario, database_url) as (session, scenario):
            self.scenario = (
                session.query(Scenario).filter(Scenario.id == scenario.id).one()
            )

            annual_fleet_mileage = get_annual_fleet_mileage(session, self.scenario)
            self.annual_fleet_mileage = annual_fleet_mileage
            self.energy_consumption_mode = energy_consumption_mode
            if self.energy_consumption_mode == "constant":
                assert "const_energy_consumption" in self.scenario.tco_parameters, (
                    "const_energy_consumption must be provided in the scenario tco_parameters when energy_consumption_mode is 'constant'"
                )

                const_energy_consumption = self.scenario.tco_parameters["const_energy_consumption"]
                self.const_energy_consumption = const_energy_consumption

            if capex_items is None:
                self._load_capex_items_from_db(session)

            else:
                raise NotImplementedError(
                    "Using your own list of dictonary then setting up list of capex items is not implemented yet. Please use the database to load the capex items."
                )
            if opex_items is None:

                self.opex_items = self._load_opex_items_from_db(
                        session)
            else:
                raise NotImplementedError(
                    "Using your own list of dictonary then setting up list of opex items is not implemented yet. Please use the database to load the opex items."
                )

            # initialize scenario related data
            self.project_duration = self.scenario.tco_parameters["project_duration"]
            self.interest_rate = self.scenario.tco_parameters["interest_rate"]
            self.inflation_rate = self.scenario.tco_parameters["inflation_rate"]

            # Initialize the output values
            self.total_capex = 0
            self.total_opex = 0
            self.tco_over_project_duration = 0
            self.tco_unit_distance = 0
            self.tco_by_item = pd.DataFrame(columns=["Item", "Specific Cost", "Type"])


    def calculate(self):
        """
        Calculate the total cost of ownership based on the input data provided in the dictionaries.
        :return: A dictionary containing the TCO results.
        """

        list_of_items = []
        list_of_costs = []
        # ----------Total CAPEX----------#

        # Calculate the total cost for each asset over the project duration.
        for capex_item in self.capex_items:
            # Calculate the procurement cost for the respective asset including replacement.
            procurement_this_type = (
                capex_item.calculate_total_procurement_cost(
                    project_duration=self.project_duration,
                    interest_rate=self.interest_rate,
                    net_discount_rate=self.inflation_rate,
                )
                * capex_item.quantity
            )
            # Add the cost of this asset to the CAPEX section of the TCO.

            # self.tco_by_item[capex_item] = procurement_this_type
            list_of_items.append(capex_item)
            list_of_costs.append(procurement_this_type)
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

            # self.tco_by_item[opex_item] = total_opex_of_type
            list_of_items.append(opex_item)
            list_of_costs.append(total_opex_of_type)
            self.total_opex += total_opex_of_type

        # ----------Calculation of three kinds of TCO----------#

        # TCO over project duration
        self.tco_over_project_duration = self.total_opex + self.total_capex

        # Annual TCO
        # TODO do we need this? maybe later

        # Specific TCO over project duration
        self.tco_unit_distance = self.tco_over_project_duration / (
            self.annual_fleet_mileage * self.project_duration
        )

        # Create a DataFrame from the list of items and costs
        self.tco_by_item = pd.DataFrame({"Item": list_of_items, "Cost": list_of_costs})

        self.tco_by_item["Specific Cost"] = self.tco_by_item["Cost"] / (
            self.annual_fleet_mileage * self.project_duration
        )
        self.tco_by_item["type"] = self.tco_by_item["Item"].apply(lambda x: x.type.name)

        tco_by_type = {}

        types = set(self.tco_by_item["type"].values)
        for t in types:
            tco_by_type[t] = self.tco_by_item[self.tco_by_item["type"] == t][
                "Specific Cost"
            ].sum()

        self.tco_by_type = tco_by_type

        tco_by_type_without_staff = tco_by_type.copy()
        tco_by_type_without_staff.pop("STAFF", None)
        self.tco_by_type_without_staff = tco_by_type_without_staff


    def visualize(self):
        """
        Visualize the TCO results.
        """


        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 8))
        bottom = 0
        for item_type, cost in self.tco_by_type.items():
            current_bar = ax.bar(
                "Total TCO",
                cost,
                bottom=bottom,
                label=item_type,
                width=0.2,
            )
            bottom += cost
            ax.bar_label(current_bar, label_type="center", padding=3, fmt="%.2f")

        total = self.tco_unit_distance
        ax.text(0, total + 0.05, str(round(total, 2)), ha="center", va="bottom", fontweight="bold")
        ax.set_ylabel("Specific Cost (EUR/km)")
        ax.set_xlim(left=-0.5, right=0.5)
        ax.set_title("Total Cost of Ownership by Type")
        ax.legend()
        plt.savefig("tco_by_type.png")


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

    def _load_opex_items_from_db(self, session):
        """
        This method returns the opex input dictionary, which is used to calculate the TCO.
        :return: A dictionary including the opex input data.
        """

        list_opex_items = []

        scenario_tco_parameters = self.scenario.tco_parameters

        # Get the annual driver hours

        # TODO should we avoid using OpexItem here?

        total_driver_hours = calculate_total_driver_hours(session, self.scenario)
        staff_cost = OpexItem(
            name="Staff Cost",
            type=OpexItemType.STAFF,
            unit_cost=scenario_tco_parameters["staff_cost"],
            usage_amount=total_driver_hours,
            cost_escalation=scenario_tco_parameters["pef_wages"],
        )
        list_opex_items.append(staff_cost)

        # Get the total energy consumption
        match self.energy_consumption_mode:
            case "constant":
                total_energy_consumption = 0.0
                mileage_per_vt = get_mileage_per_vehicle_type(session, self.scenario)
                for vid, consumption in self.const_energy_consumption.items():
                    if vid in mileage_per_vt:
                        total_energy_consumption += consumption * mileage_per_vt[vid]


            case "simulated":
                total_energy_consumption = calc_energy_consumption_simulated(session, self.scenario)
            case _:
                raise ValueError(f"Unknown energy consumption mode: {self.energy_consumption_mode}")
        # total_energy_consumption = calc_energy_consumption_simulated(session, self.scenario)

        # TODO maybe change it to energy_cost
        fuel_cost = OpexItem(
            name="Fuel Cost",
            type=OpexItemType.ENERGY,
            unit_cost=scenario_tco_parameters["fuel_cost"],
            usage_amount=total_energy_consumption,
            cost_escalation=scenario_tco_parameters["pef_fuel"],
        )
        list_opex_items.append(fuel_cost)

        # Get the total fleet mileage

        maint_cost_vehicles = OpexItem(
            name="Maintenance Cost Vehicles",
            type=OpexItemType.MAINTENANCE,
            unit_cost=scenario_tco_parameters["maint_cost"],
            usage_amount=self.annual_fleet_mileage,
            cost_escalation=scenario_tco_parameters["pef_general"],
        )
        list_opex_items.append(maint_cost_vehicles)

        total_number_vehicles = sum(
            asset.quantity
            for asset in self.capex_items
            if asset.type == CapexItemType.VEHICLE
        )
        insurance = OpexItem(
            name="Insurance",
            type=OpexItemType.OTHER,
            unit_cost=scenario_tco_parameters["insurance"],
            usage_amount=total_number_vehicles,
            cost_escalation=scenario_tco_parameters["pef_insurance"],
        )
        list_opex_items.append(insurance)

        taxes = OpexItem(
            name="Taxes",
            type=OpexItemType.OTHER,
            unit_cost=scenario_tco_parameters["taxes"],
            usage_amount=total_number_vehicles,
            cost_escalation=scenario_tco_parameters["pef_general"],
        )
        list_opex_items.append(taxes)

        total_number_charging_points = sum(
            asset.quantity
            for asset in self.capex_items
            if asset.type == CapexItemType.CHARGING_POINT
        )
        maint_cost_infra = OpexItem(
            name="Maintenance Cost Infrastructure",
            type=OpexItemType.MAINTENANCE,
            unit_cost=scenario_tco_parameters["maint_infr_cost"],
            usage_amount=total_number_charging_points,
            cost_escalation=scenario_tco_parameters["pef_general"],
        )
        list_opex_items.append(maint_cost_infra)

        return list_opex_items

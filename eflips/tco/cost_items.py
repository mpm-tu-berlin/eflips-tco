from dataclasses import dataclass
from enum import Enum, auto

from eflips.tco.tco_utils import replacement_cost, annuity, net_present_value
class CapexItemType(Enum):
    """
    """

    VEHICLE = auto()
    "For a vehicle asset, annual mileage is required in the asset parameters."

    BATTERY = auto()
    "For a battery asset, the battery capacity is required in the asset parameters. The procurement cost is the cost per kWh."

    INFRASTRUCTURE = auto()

    CHARGING_POINT = auto()


@dataclass
class CapexItem:
    """
    A general class describing an asset. It is used in the calculation of CAPEX and should include the following parameters:

    """

    name: str
    useful_life: int
    procurement_cost: float
    cost_escalation: float
    quantity: int
    asset_type: CapexItemType

    def calculate_total_procurement_cost(
            self,
            project_duration: int,
            interest_rate: float = 0.04,
            net_discount_rate: float = 0.02,
    ):
        """ """
        # Get a list with all procurements taking place over the project duration
        all_procurements = replacement_cost(
            self.procurement_cost,
            self.cost_escalation,
            self.useful_life,
            project_duration,
        )
        # List with all annuities
        annuities: list[float] = []
        annuities_pv: list[float] = []
        # Includes the scaled down present value of the last replacement in case the useful life is larger than the
        # remaining project duration.
        # Calculating all annuities over the project duration and saving them in a list
        for new_price, years_after_base_year, partially_used in all_procurements:
            annuity_this = annuity(new_price, self.useful_life, interest_rate)
            if partially_used:
                # Calculate the present value of the last replacement, scaled for partial use
                annuities_last_replacement = [annuity_this] * self.useful_life
                pv_sum = sum(
                    net_present_value(ann, year, net_discount_rate)
                    for year, ann in enumerate(annuities_last_replacement)
                )
                fraction_used = (
                                        project_duration - years_after_base_year
                                ) / self.useful_life
                scaled_down_CF = pv_sum * fraction_used
                annuities.append(scaled_down_CF)
            else:
                # Add the annuity for each year of the asset's useful life
                annuities.extend([annuity_this] * self.useful_life)

        # Calculate the present value of all cashflows at the base year
        annuities_pv.extend(
            net_present_value(ann, year, net_discount_rate)
            for year, ann in enumerate(annuities)
        )
        # The total procurement cost is returned which is the sum of the annuities adjusted for inflation / discount
        # rate.
        return sum(annuities_pv)


@dataclass
class OpexItem:
    """
    A general class describing an OPEX item. It is used in the calculation of OPEX and should include the following parameters:
    """

    name: str
    unit_cost: float
    usage_amount: float
    cost_escalation: float

    def future_cost(self, years_after_base_year: int):
        """
        This method calculates the future cost of the OPEX item based on the cost escalation factor and the usage amount.

        :param years_after_base_year: The year after the base year in which the cost arises.
        :return: The future cost of the OPEX item in the respective year.
        """
        return (
                self.unit_cost
                * (1 + self.cost_escalation) ** years_after_base_year
                * self.usage_amount
        )

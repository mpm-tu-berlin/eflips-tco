"""Dataclass definitions for TCO parameters and results."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class VehicleTypeTCOParameter:
    """TCO parameters for a vehicle type."""

    name_short: str
    useful_life: int
    procurement_cost: float
    cost_escalation: float
    name: Optional[str] = None
    average_electricity_consumption: Optional[float] = None
    average_diesel_consumption: Optional[float] = None

    def __post_init__(self):
        if (self.average_electricity_consumption is None) == (
            self.average_diesel_consumption is None
        ):
            raise ValueError(
                "Exactly one of average_electricity_consumption or average_diesel_consumption must be set."
            )

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "useful_life": self.useful_life,
            "procurement_cost": self.procurement_cost,
            "cost_escalation": self.cost_escalation,
        }
        if self.average_electricity_consumption is not None:
            d["average_electricity_consumption"] = self.average_electricity_consumption
        else:
            d["average_diesel_consumption"] = self.average_diesel_consumption
        return d


@dataclass
class BatteryTypeTCOParameter:
    """TCO parameters for a battery type."""

    vehicle_name_short: str
    procurement_cost: float
    useful_life: int
    cost_escalation: float
    # Required only when no BatteryType exists yet for the associated VehicleType.
    specific_mass: Optional[float] = None
    chemistry: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "procurement_cost": self.procurement_cost,
            "useful_life": self.useful_life,
            "cost_escalation": self.cost_escalation,
        }


@dataclass
class ChargingPointTypeTCOParameter:
    """TCO parameters for a charging point type."""

    type: str
    procurement_cost: float
    useful_life: int
    cost_escalation: float
    # Required only when no ChargingPointType exists yet for the associated depot/station.
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "procurement_cost": self.procurement_cost,
            "useful_life": self.useful_life,
            "cost_escalation": self.cost_escalation,
        }


@dataclass
class ChargingInfrastructureTCOParameter:
    """TCO parameters for charging infrastructure."""

    type: str
    procurement_cost: float
    useful_life: int
    cost_escalation: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "procurement_cost": self.procurement_cost,
            "useful_life": self.useful_life,
            "cost_escalation": self.cost_escalation,
        }


@dataclass
class ScenarioTCOParameter:
    """TCO parameters for a scenario.

    Format follows eflips-opt transition planning convention.

    Required fields:
    - project_duration, interest_rate, inflation_rate: financial framing
    - staff_cost: driver cost per hour
    - fuel_cost: dict with "diesel" and "electricity" keys (EUR/l and EUR/kWh)
    - vehicle_maint_cost: dict with "diesel" and "electricity" keys (EUR/km)
    - infra_maint_cost: annual infrastructure maintenance per charging point
    - cost_escalation_rate: dict with "general", "staff", "diesel", "electricity",
      "insurance" keys (annual rate)
    - insurance: annual insurance per vehicle
    - taxes: annual taxes per vehicle

    Optional fields (used by transition planner):
    - annual_budget_limit: max annual investment budget
    - depot_time_plan: dict mapping depot name to electrification year
    - current_year: base year for the planning horizon
    - max_station_construction_per_year: max new stations per year
    """

    project_duration: int
    interest_rate: float
    inflation_rate: float
    staff_cost: float
    fuel_cost: Dict[str, float]
    vehicle_maint_cost: Dict[str, float]
    infra_maint_cost: float
    cost_escalation_rate: Dict[str, float]
    insurance: float
    taxes: float
    annual_budget_limit: Optional[float] = None
    depot_time_plan: Optional[Dict[str, int]] = None
    current_year: Optional[int] = None
    max_station_construction_per_year: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Remove None optional fields so they don't clutter the stored dict
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class TCOResult:
    """Aggregated TCO results for a scenario, produced by :class:`TCOCalculator.calculate`."""

    project_duration: int
    """Project duration in years."""

    annual_fleet_mileage: float
    """Annual fleet mileage in km/year."""

    total_capex: float
    """Total CAPEX (net present value) over the project duration in EUR."""

    total_opex: float
    """Total OPEX (net present value) over the project duration in EUR."""

    tco_over_project_duration: float
    """Total TCO (CAPEX + OPEX, net present value) in EUR."""

    tco_per_km: float
    """Specific TCO in EUR/km over the total fleet-km of the project duration."""

    tco_by_type: Dict[str, float]
    """Specific TCO (EUR/km) broken down by cost category (e.g. VEHICLE, ENERGY, STAFF)."""

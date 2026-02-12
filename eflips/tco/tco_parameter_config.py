"""Dataclass definitions for TCO parameters."""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class VehicleTypeTCOParameter:
    """TCO parameters for a vehicle type."""

    name_short: str
    name: str
    useful_life: int
    procurement_cost: float
    cost_escalation: float
    const_energy_consumption: Optional[float] = None

    def to_dict(self, vehicle_id: int) -> Dict[str, Any]:
        d = {
            "id": vehicle_id,
            "name": self.name,
            "useful_life": self.useful_life,
            "procurement_cost": self.procurement_cost,
            "cost_escalation": self.cost_escalation,
        }
        if self.const_energy_consumption is not None:
            d["const_energy_consumption"] = self.const_energy_consumption
        return d


@dataclass
class BatteryTypeTCOParameter:
    """TCO parameters for a battery type."""

    name: str
    vehicle_name_short: str
    procurement_cost: float
    useful_life: int
    cost_escalation: float
    vehicle_type_id: Optional[int] = None
    # Used when creating a new BatteryType in the database (i.e. no existing BatteryType
    # is found for the associated VehicleType). These provide the required model fields.
    specific_mass: float = 1.0
    chemistry: str = "unknown"

    def to_dict(self, battery_id: Optional[int] = None) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "vehicle_name_short": self.vehicle_name_short,
            "procurement_cost": self.procurement_cost,
            "useful_life": self.useful_life,
            "cost_escalation": self.cost_escalation,
        }
        if battery_id is not None:
            d["id"] = battery_id
        if self.vehicle_type_id is not None:
            d["vehicle_type_id"] = self.vehicle_type_id
        return d


@dataclass
class ChargingPointTypeTCOParameter:
    """TCO parameters for a charging point type."""

    type: str
    name: str
    procurement_cost: float
    useful_life: int
    cost_escalation: float

    def to_dict(self, charger_id: Optional[int] = None) -> Dict[str, Any]:
        d = {
            "type": self.type,
            "name": self.name,
            "procurement_cost": self.procurement_cost,
            "useful_life": self.useful_life,
            "cost_escalation": self.cost_escalation,
        }
        if charger_id is not None:
            d["id"] = charger_id
        return d


@dataclass
class ChargingInfrastructureTCOParameter:
    """TCO parameters for charging infrastructure."""

    type: str
    name: str
    procurement_cost: float
    useful_life: int
    cost_escalation: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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

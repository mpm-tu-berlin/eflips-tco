"""Berlin TCO parameter defaults from literature.

Prices taken from Jefferies and Goehlich (2020), with inflation adjustment.
"""

from eflips.tco.tco_parameter_config import (
    VehicleTypeTCOParameter,
    BatteryTypeTCOParameter,
    ChargingPointTypeTCOParameter,
    ChargingInfrastructureTCOParameter,
    ScenarioTCOParameter,
)

# Vehicle type defaults
VEHICLE_TYPES = [
    VehicleTypeTCOParameter(
        name_short="EN",
        name="Ebusco 3.0 12 large battery",
        useful_life=14,
        procurement_cost=580000.0,
        cost_escalation=-0.02,
        average_electricity_consumption=1.48,
    ),
    VehicleTypeTCOParameter(
        name_short="DD",
        name="Solaris Urbino 18 large battery",
        useful_life=14,
        procurement_cost=780000.0,
        cost_escalation=-0.02,
        average_electricity_consumption=2.16,
    ),
    VehicleTypeTCOParameter(
        name_short="GN",
        name="Alexander Dennis Enviro500EV large battery",
        useful_life=14,
        procurement_cost=780000.0,
        cost_escalation=-0.02,
        average_electricity_consumption=2.16,
    ),

    VehicleTypeTCOParameter(
        name_short="Diesel EN",
        name="Diesel Ebusco 3.0 12 large battery",
        useful_life=14,
        procurement_cost=275000.0,
        cost_escalation=0.02,
        average_diesel_consumption=0.449,
    ),
    VehicleTypeTCOParameter(
        name_short="Diesel DD",
        name="Diesel Solaris Urbino 18 large battery",
        useful_life=14,
        procurement_cost=330000.0,
        cost_escalation=0.02,
        average_diesel_consumption=0.589,
    ),
    VehicleTypeTCOParameter(
        name_short="Diesel GN",
        name="Diesel Alexander Dennis Enviro500EV large battery",
        useful_life=14,
        procurement_cost=510000.0,
        cost_escalation=0.02,
        average_diesel_consumption=0.589,
    ),
]

# Battery type defaults
BATTERY_TYPES = [
    BatteryTypeTCOParameter(
        vehicle_name_short="EN",
        procurement_cost=190,
        useful_life=7,
        cost_escalation=-0.03,
        specific_mass=0.1,
        chemistry="test",
    ),
    BatteryTypeTCOParameter(
        vehicle_name_short="DD",
        procurement_cost=190,
        useful_life=7,
        cost_escalation=-0.03,
        specific_mass=0.1,
        chemistry="test",
    ),
    BatteryTypeTCOParameter(
        vehicle_name_short="GN",
        procurement_cost=190,
        useful_life=7,
        cost_escalation=-0.03,
        specific_mass=0.1,
        chemistry="test",
    ),
]

# Charging point defaults
# Prices from Jefferies and Goehlich (2020), with inflation adjustment
CHARGING_POINT_TYPES = [
    ChargingPointTypeTCOParameter(
        name="depot",
        type="depot",
        procurement_cost=119899.50,
        useful_life=20,
        cost_escalation=0.02,
    ),
    ChargingPointTypeTCOParameter(
        name="station",
        type="opportunity",
        procurement_cost=299748.74,
        useful_life=20,
        cost_escalation=0.02,
    ),
]

# Charging infrastructure defaults
CHARGING_INFRASTRUCTURE = [
    ChargingInfrastructureTCOParameter(
        type="depot",
        procurement_cost=2397989.95,  # TODO
        useful_life=20,
        cost_escalation=0.02,
    ),
    ChargingInfrastructureTCOParameter(
        type="station",
        procurement_cost=269773.87,
        useful_life=20,
        cost_escalation=0.02,
    ),
]

# Scenario TCO parameters
SCENARIO_TCO = ScenarioTCOParameter(
    project_duration=20,
    interest_rate=0.04,
    inflation_rate=0.02,
    staff_cost=25.0,  # calculated: 35,000 EUR p.a. per driver / 1600 h p.a. per driver
    fuel_cost={"diesel": 1.5, "electricity": 0.1794},
    vehicle_maint_cost={"diesel": 0.35, "electricity": 0.35},
    infra_maint_cost=1000,  # maintenance cost infrastructure per year and charging slot
    cost_escalation_rate={
        "general": 0.02,
        "staff": 0.025,
        "diesel": 0.0,
        "electricity": 0.038,
        "insurance": 0.02,
    },
    insurance=9693,  # DCO #9703, # EBU
    taxes=278,       # taxes in EUR per year and bus
)

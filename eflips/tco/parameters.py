"""
The parameters are defined in the beginning of the code, later,
they should be put in by feeding a list into the program.
"""

""" project duration in years """
project_duration = 12

# Some cost escalation factors.
cef_vehicles = 0.025
cef_battery = -0.03
cef_infra = 0.02

"""
CAPEX
"""

""" Annual interest and inflation rate """
interest_rate = 0.04
inflation_rate = 0.025

# asset specific lists including: (asset_name, procurement_cost, useful_life, cost_escalation)
Vehicles = [
    ("Ebusco 3.0 12 large battery", 370000.0, 12, cef_vehicles),
    ("Ebusco 3.0 12 small battery", 370000.0, 12, cef_vehicles),
    ("Solaris Urbino 18 large battery", 603000.0, 12, cef_vehicles),
    ("Solaris Urbino 18 small battery", 603000.0, 12, cef_vehicles),
    ("Alexander Dennis Enviro500EV large battery", 700000.0, 12, cef_vehicles),
    ("Alexander Dennis Enviro500EV small battery", 700000.0, 12, cef_vehicles),
]


def vehicle_dict():
    Vehicle_dict = {
        name: {"procurement_cost": proc, "useful_life": uf, "cost_escalation": cef}
        for name, proc, uf, cef in Vehicles
    }
    return Vehicle_dict


# procurement cost per kWh
Battery = [
    ("Ebusco 3.0 12 large battery", 350, 6, cef_battery),
    ("Ebusco 3.0 12 small battery", 350, 6, cef_battery),
    ("Solaris Urbino 18 large battery", 350, 6, cef_battery),
    ("Solaris Urbino 18 small battery", 350, 6, cef_battery),
    ("Alexander Dennis Enviro500EV large battery", 350, 6, cef_battery),
    ("Alexander Dennis Enviro500EV small battery", 350, 6, cef_battery),
]


def battery_dict():
    Battery_dict = {
        name: {"procurement_cost": proc, "useful_life": uf, "cost_escalation": cef}
        for name, proc, uf, cef in Battery
    }
    return Battery_dict


Charging_Stations = [
    ("OPPORTUNITY Station", 500000, 20, cef_infra),  # OPPORTUNITY charging station
    ("300 kw_Slot", 275000, 20, cef_infra),  # OPPORTUNITY charging slot
    ("DEPOT Station", 3400000, 20, cef_infra),  # DEPOT charging station
    ("120 kw_Slot", 100000, 20, cef_infra),  # DEPOT charging slot
]


def charging_stations_dict():
    Charging_Stations_dict = {
        name: {"procurement_cost": proc, "useful_life": uf, "cost_escalation": cef}
        for name, proc, uf, cef in Charging_Stations
    }
    return Charging_Stations_dict


""" 
OPEX
"""

""" hourly staff cost in EUR per driver """
staff_cost = 21.875  # calculated: 35,000 € p.a. per driver/1600 h p.a. per driver
annual_staff_cost = 35000

""" Fuel cost in EUR per unit fuel """
fuel_cost = 0.1794  # electricity cost

""" Maintenance cost in EUR per km """
maint_cost = 0.35

"""Maintenance cost infrastructure per year and charging slot."""
maint_infr_cost = 1000

""" Taxes and insurance cost in EUR per year and bus"""
taxes = 400.50
insurance = 300

""" Cost escalation factors (cef / pef). There should be multiple CEFS for different categories."""
pef_general = 0.02
pef_wages = 0.02
pef_fuel = 0.038
pef_insurance = 0.1

""" Simulation period can be manually inserted"""
sim_period = None

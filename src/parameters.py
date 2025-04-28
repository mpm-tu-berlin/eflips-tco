"""
The parameters are defined in the beginning of the code, later,
they should be put in by feeding a list into the program.
"""

""" project duration in years """
project_duration = 20

"""
CAPEX
"""

""" Annual interest and inflation rate """
interest_rate = 0.04
inflation_rate = 0.025

# asset specific lists including: (asset_name, procurement_cost, useful_life, cost_escalation)
Vehicles = [
    ("Ebusco 3.0 12", 370000, 12, 0.025),
    ("Solaris Urbino 18", 603000, 12, 0.025),
    ("Alexander Dennis Enviro500EV", 700000, 12, 0.025)
]
# procurement cost per kWh
Battery = [
    ("Ebusco 3.0 12", 350, 6, -0.03),
    ("Solaris Urbino 18",  350, 6, -0.03),
    ("Alexander Dennis Enviro500EV", 350, 6, -0.03)
]
Charging_Stations = [
    ("OC-station", 500000, 20, 0.02),
    ("OC-slot", 275000, 20, 0.02),
    ("DC-station", 3400000, 20, 0.02),
    ("DC-slot", 500000, 20, 0.02)
]
""" 
OPEX
"""

""" hourly staff cost in EUR per driver """
staff_cost = 21.875 # calculated: 35,000 € p.a. per driver/1600 h p.a. per driver
annual_staff_cost = 35000

""" Fuel cost in EUR per unit fuel """
fuel_cost = 0.1794 #electricity cost

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

""" Sumulation period can be manually inserted"""
sim_period = None
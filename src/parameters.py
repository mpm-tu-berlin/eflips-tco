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

""" Procurement cost in EUR """
proc_12m_beb = 370000
proc_18m_beb = 603000

""" Procurement battery in € per kWh."""
proc_battery = 350

""" depot charging (dc)"""
proc_dc_station = 3400000
proc_dc_slot = 100000

""" terminal stop charging (tsc)"""
proc_tsc_station = 500000
proc_tsc_slot = 275000

""" Useful life in years"""
uf_12m_beb = 12
uf_18m_beb = 12
uf_battery = 6 # must be an integer divisor of the useful life of the buses.
uf_dc_station = 20
uf_dc_slot = 20
uf_tsc_station = 20
uf_tsc_slot = 20

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

""" Price escalation factors (pef). There should be multiple pefs for different categories."""
pef_general = 0.02
pef_wages = 0.02
pef_battery = -0.03
pef_fuel = 0.038
cef_vehicle = 0.025

""" Sumulation period can be manually inserted"""
sim_period = None
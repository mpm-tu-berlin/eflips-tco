"""
The parameters are defined in the beginning of the code, later,
they should be put in by feeding a list into the program.
"""

#project duration in years
project_duration = 12


#CAPEX

# Cost escalation factors (cef). There should be multiple CEFS for different categories.
cef_general = 0.02
cef_wages = 0.025
cef_fuel = 0.007
cef_insurance = 0.02
cef_vehicles = 0.02
cef_battery = -0.0
cef_infra = 0.0

# Annual interest and discount rate.
interest_rate = 0.04
discount_rate = 0.02

# asset specific lists including: (asset_name, procurement_cost, useful_life, cost_escalation).
# The contents are loaded from the input file.
Vehicles = [
    #(0,"Ebusco 3.0 12", 400000.0, 12, cef_vehicles),
    #(0,"Solaris Urbino 18", 603000.0, 12, cef_vehicles),
    #(0,"Alexander Dennis Enviro500EV", 850000.0, 12, cef_vehicles)
]

def vehicle_dict():
    Vehicle_dict = {
        name: {"procurement_cost": proc, "useful_life": uf, "cost_escalation": cef}
        for name, proc, uf, cef in Vehicles
    }
    return Vehicle_dict

# procurement cost per kWh
Battery = [
    #(0,"Ebusco 3.0 12", 350, 6, cef_battery),
    #(0,"Solaris Urbino 18",  350, 6, cef_battery),
    #(0,"Alexander Dennis Enviro500EV", 350, 6, cef_battery)
]

def battery_dict():
    Battery_dict = {
        name: {"procurement_cost": proc, "useful_life": uf, "cost_escalation": cef}
        for name, proc, uf, cef in Battery
    }
    return Battery_dict

Charging_Stations = [
    ("OPPORTUNITY Station", 500000, 20, cef_infra), # OPPORTUNITY charging station
    ("300 kw_Slot", 275000, 20, cef_infra),  # OPPORTUNITY charging slot
    ("DEPOT Station", 3400000, 20, cef_infra), # DEPOT charging station
    ("120 kw_Slot", 100000, 20, cef_infra) # DEPOT charging slot
]

def charging_stations_dict():
    Charging_Stations_dict = {
        name: {"procurement_cost": proc, "useful_life": uf, "cost_escalation": cef}
        for name, proc, uf, cef in Charging_Stations
    }
    return Charging_Stations_dict


#OPEX


# hourly staff cost in EUR per driver
staff_cost = 25
#annual_staff_cost = 35000

# Fuel cost in EUR per unit fuel
fuel_cost = 0.1794 #electricity cost

# Maintenance cost in EUR per km
maint_cost = 0.35

# Maintenance cost infrastructure per year and charging slot.
maint_infr_cost = 1000

#Taxes and insurance cost in EUR per year and bus.
taxes = 278
insurance = 9697

# Simulation period is obtained in get_data.py.
sim_period = None
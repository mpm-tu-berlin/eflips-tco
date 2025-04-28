import numpy as np

import get_data
import parameters as p

def net_present_value(cash_flow, years_after_base_year: int, discount_rate = 0.02):
    """
    This method is used to calculate the net present value of any cash flow, a default value for the discount rate is set.

    :param cash_flow: The cashflow of which the present value needs to be calculated.
    :param years_after_base_year: The year after the base year in which the cashflow occurs.
    :param discount_rate: The discount rate by which the cash flow should be discounted.
    :return: A tuple of the present value of the cashflow rounded on 2 decimals and the year after base year in which the cashflow occurs.
    """
    npv = cash_flow / ((1 + discount_rate)**years_after_base_year)
    return round(npv,2), years_after_base_year


def annuity(procurement_cost: float, useful_life: int, interest_rate = 0.04):
    """
    This method is used to calculate the annuity of an asset, a default value for the interest rate is set.

    :param procurement_cost: The procurement cost of the respective asset of which the annuty should be calculated.
    :param useful_life: The useful life of the respective asset, which is also the time over which the asset is financed.
    :param interest_rate: The interest rate which is the cost of the capital needed to procure the respective asset.
    :return: The value of the annuity rounded to 2 decimals.
    """
    ann = procurement_cost*interest_rate / (1-(1+interest_rate)**(-useful_life))
    return round(ann, 2)

""" This method is used to calculate the total procurement cost of a single asset taking the annuities and the inflation into account. """
def total_proc(procurement_cost: float, useful_life: int, project_duration: int, interest_rate = 0.01, net_discount_rate = 0.02):
    annuities = np.zeros(useful_life)
    annuity_this_component = annuity(procurement_cost, useful_life, interest_rate)
    for i in range(useful_life):
        annuities[i] = net_present_value(annuity_this_component, i, net_discount_rate)[0]
    return sum(annuities)*project_duration/useful_life #hier wird noch keine wiederbeschaffung mit entsprechenden preissteigerungsfaktoren berücksichtigt.


def future_cost(cef, base_price, years_after_base_year):
    """
    This method is used to calculate the costs of a certain category at a certain time taking into account the price escalation factors (pef).

    :param cef: The cost escalation factor which represents the annual change of the costs / prices.
    :param base_price: The price in the base year.
    :param years_after_base_year: The years after the base year in which the cost arises.
    :return: The cost in the respective year and the year after the base year in which the cost arises.
    """
    cost = base_price * (1+cef)**years_after_base_year
    return round(cost, 2), years_after_base_year


def replacement_cost(base_price, cost_escalation, useful_life, project_duration):
    """
    In this method, the replacement costs of an asset are calculated considering the cost escalation.

    :param base_price: The price in the base year.
    :param cost_escalation: The cost escalation factor which represents the annual change of the costs / prices.
    :param useful_life: The useful life of the respective asset.
    :param project_duration: The duration of the project as a timeframe that is considered in this calculation.
    :return: The replacement cost as well as the number of years after the base year in which the replacemtn is conducted are returned with a binary variable which shows whether the useful life of the replaced asset is still within the project duration.
    """
    replacement: list[float, int, bool] = []
    # get the number of full replacements
    number_of_full_replacements = project_duration // useful_life
    for i in range(number_of_full_replacements+1):
        # The new price is the baseprice multiplied by the cost escalation factor to the power of the years after the base year.
        new_price = base_price * (1 + cost_escalation) ** (i * useful_life)
        # If the project ends before the useful life if the next replacement, the binary variable is set true in order to account for that later.
        if (i+1)*useful_life < project_duration:
            replacement.append((new_price, i*useful_life, False))
        elif (i+1)*useful_life == project_duration:
            replacement.append((new_price, i * useful_life, False))
            break
        else:
            # The useful
            replacement.append((new_price, i*useful_life, True))
            break
    return replacement


def total_proc_cef(procurement_cost: float, useful_life: int, project_duration: int, cost_escalation: float, interest_rate = 0.04, net_discount_rate = 0.02):
    """
    This method calculates the procurement cost of an asset over its lifetime while also accounting for partial consideration.

    :param procurement_cost: The procurement cost of the respective asset of which the annuty should be calculated.
    :param useful_life: The useful life of the respective asset, which is also the time over which the asset is financed.
    :param project_duration: The duration of the project as a timeframe that is considered in this calculation.
    :param cost_escalation: The cost escalation factor which represents the annual change of the costs / prices.
    :param interest_rate: The interest rate which is the cost of the capital needed to procure the respective asset.
    :param net_discount_rate: The discount rate by whixch the cashflows are discounted.
    :return: The total procurement cost of the respective asset over the project duration considering the cost escalation and the present value
    """
    # Get a list with all procurements taking place over the project duration
    all_procurements = replacement_cost(procurement_cost, cost_escalation, useful_life, project_duration)
    # List with all annuities
    annuities: list[float] = []
    annuities_pv = np.zeros(project_duration)
    # Calculating all annuities over the project duration and saving them in a list
    for i in range(len(all_procurements)):
        annuity_this = annuity(all_procurements[i][0], useful_life, interest_rate)
        if all_procurements[i][2]:
            # Only the annuities within the project duration are considered
            for j in range(project_duration-all_procurements[i][1]):
                annuities.append(annuity_this)
        else:
            #For every year the respective annuity is appended to the list
            for j in range(useful_life):
                annuities.append(annuity_this)
    # The present value of the annuities is calculated
    for i in range(project_duration):
        annuities_pv[i] = net_present_value(annuities[i], i, net_discount_rate)[0]
    # The total procurement cost is returned which is the sum of the annuities adjusted for inflation / discount rate.
    return sum(annuities_pv)


def sim_period_to_year(session, scenario, sim_period = None):
    """
    This method is used to calculate a factor by which the quantities obtained from the simulation need to be multiplied
    with to obtain the quantities for one whole year.

    :param session: The session object.
    :param scenario: The scenario object.
    :param sim_period: The simulation period over which the simulation in eFLIPS is conducted.
    :return: A factor by which all time dependent values obtained from eFLIPS need to be multiplied to obtain annual values.
    """
    if sim_period == None:
        sim_period = get_data.get_simulation_period(session, scenario).total_seconds()/86400
    return 365.25/sim_period


def calculate_total_staff_cost(driver_hours, annual_driver_cost, annual_hours_per_driver = 1600, buffer = 0.1):
    """
    This method calculates the total staff cost based on the number of drivers required for the operation of the buses.
    The buffer variable is the amount of hours added to the pure driving time and accounts for the time the drivers work
    but are not operating the bus.

    :param driver_hours: The amount of time the buses are operated by a driver.
    :param annual_driver_cost: The cost of a single bus driver per year.
    :param annual_hours_per_driver: The time a driver work over the course of one year.
    :param buffer: An additional factor which raises the total driver hours in order to account for any additional time in which the bus is not operated but the driver is still working.
    :return: A tuple of the number of drivers and the total staff cost in one year.
    """
    # Integers are required, so the % is used
    number_drivers = driver_hours*(1+buffer)%annual_hours_per_driver
    return (number_drivers, annual_driver_cost*number_drivers)

def make_parameter_list(list_from_DB, asset_input_data,):
    """
    This method makes a list of the required parameters using for a certain asset. This enables the program to calculate
    the TCO of scenarios with a variety of different vehicle types. The method matches the asset type obtained from eFLIPS
    with the respective item of the list in parameter.py. The matching is done based on the name of the assets.
    :param list_from_DB: A list with input parameters obtained from eFLIPS. The structure mus be as such: list[tuples[scenario.id, asset_type.name, asset_type.count]
    :param asset_input_data: A lsit containing the financial input data of the asset. (asset_name, asset_cost, asset_useful_life, asset_cost_escalation).
    :return: A list if the assets including all necessary information to calculate the TCO.
    """
    # In order to calculate the TCO, a list with tuples is created. The tuples contain the name, the number, the
    # procurement cost, the useful life and the cost escalation.
    assets: list[tuple[str, int, float, int, float]] = []
    for i in range(len(list_from_DB)):
        # Finding the right procurement cost, useful life and costescalation from the asset input data list.
        procurement = useful_life = CEFs = None
        for j in range(len(asset_input_data)):
            if list_from_DB[i][1] == asset_input_data[j][0]:
                procurement = asset_input_data[j][1]
                useful_life = asset_input_data[j][2]
                CEFs = asset_input_data[j][3]
        assets.append((list_from_DB[i][1], list_from_DB[i][2], procurement, useful_life, CEFs))
        # Test whether all required buses have been put in by the user.
        if None in assets[i]:
            print("Please check the input data and add all parameters. You need to add missing parameters for the asset:",
                  list_from_DB[i][1])
    return assets
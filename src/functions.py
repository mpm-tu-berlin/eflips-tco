import numpy as np
import csv
import get_data
import parameters as p
import warnings as w


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
    replacement: list[tuple[float, int, bool]] = []
    # get the number of full replacements
    number_of_full_replacements = project_duration // useful_life
    for i in range(number_of_full_replacements+1):
        # The new price is the baseprice multiplied by the cost escalation factor to the power of the years after the base year.
        new_price = base_price * (1 + cost_escalation) ** (i * useful_life)
        # If the project ends before the useful life if the next replacement, the binary variable is set true in order
        # to account for that in the total_proc_cef function.
        if (i+1)*useful_life < project_duration:
            replacement.append((new_price, (i*useful_life), False))
        elif (i+1)*useful_life == project_duration:
            replacement.append((new_price, (i * useful_life), False))
            break
        else:
            # The useful life is shorter than the remaining project duration
            replacement.append((new_price, (i*useful_life), True))
            break
    return replacement


def total_proc_cef(procurement_cost: float, useful_life: int, project_duration: int, cost_escalation: float,
                   interest_rate = 0.04, net_discount_rate = 0.02):
    """
    This method calculates the procurement cost of an asset over its lifetime while also accounting for partial consideration
    of the procurement cost in case the project duration is not an integer multiple of the useful life of the considered asset.
    This is done according to the reviewed literature by scaling down the present value of the last replacement.

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
    annuities_pv: list[float] = []
    # Includes the scaled down present value of the last replacement in case the useful life is larger than the
    # remaining project duration.
    scaled_down_CF = 0
    # Calculating all annuities over the project duration and saving them in a list
    for i in range(len(all_procurements)):
        annuity_this = annuity(all_procurements[i][0], useful_life, interest_rate)
        if all_procurements[i][2]:
            # As the approach of scaling down the cashflows is selected here, the present value of the last replacement
            # is calculated and then multiplied by a factor resulting from the remaining project duration and the
            # useful life of the respective asset.
            # A new list is used in order to calculate the present value of the last replacement.
            annuities_last_replacement = []
            # Filling the list with all annuities over the useful life of the asset.
            for j in range(useful_life):
                annuities_last_replacement.append(annuity_this)
            # The present value of the annuities is calculated and then scaled down.
            scaled_down_CF = (sum(net_present_value(annuities_last_replacement[x], x, net_discount_rate)[0]
                                  for x in range(len(annuities_last_replacement))) * (project_duration - all_procurements[i][1]) / useful_life)
            # The scaled down cashflow is then appended to the list of annuities, so the present value at
            # the time of the base year can be calculated along with the other annuities.
            annuities.append(scaled_down_CF)
        else:
            #For every year the respective annuity is appended to the list.
            for j in range(useful_life):
                annuities.append(annuity_this)
    # The present value of all cashflows at the base year is calculated.
    for i in range(len(annuities)):
        annuities_pv.append(net_present_value(annuities[i], i, net_discount_rate)[0])
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
    if sim_period is None:
        sim_period = get_data.get_simulation_period(session, scenario).total_seconds()/86400
    return 365.25/sim_period

# TODO check the calculation of the staff cost as this function is not yet considered!
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

# get the input data from the input CSV file.
def read_csv(csvfile):
    """
    This method reads the csv file for the input data and changes the parameters in parameters.py to match the given
    values from the CSV file. If some values are not given, the default values from parameters.py are used instead.

    :param csvfile: The CSV file which contains the input parameters.
    :return: None, this function purely changes the input parameters in parameters.py.
    """
    input_list = list(csv.reader(csvfile, delimiter=';'))
    # Read the data for vehicle type and infrastructure type
    for i in range(len(input_list)):
        # Create lists in the format of the tuples in parameters.Vehicles, parameters.Batteries and parameters.Charging_Stations
        vehicle = [str(input_list[i][0]), cast_value(input_list[i][1], "float"),
                   cast_value(input_list[i][2], "int"), p.cef_vehicles]
        battery = [str(input_list[i][3]), cast_value(input_list[i][4], "float"),
                   cast_value(input_list[i][5], "int"), p.cef_battery]
        infra = [str(input_list[i][6]), cast_value(input_list[i][7], "float"),
                 cast_value(input_list[i][8], "int"), p.cef_infra]

        # Create lists with the names of vehicles, batteries and charging infrastructure in order to check, whether the
        # new entry needs to be appended to the list or a default value needs to be replaced
        vehicle_names = [x[0] for x in p.Vehicles]
        battery_names = [x[0] for x in p.Battery]
        infra_names = [x[0] for x in p.Charging_Stations]

        # Append new vehicle types (including battery) to the list or replace the values if this type is already in the list.
        if vehicle[0] in vehicle_names:
            if vehicle[0] not in battery_names:
                raise ValueError("Please add data for the battery type of bus {}. The vehicle_battery_name needs to be identical with {}.".format(vehicle[0], vehicle[0]))
            idx = vehicle_names.index(vehicle[0])
            p.Vehicles[idx] = tuple(vehicle)
            idx_battery = battery_names.index(battery[0])
            p.Battery[idx_battery] = tuple(battery)
        else:
            # If the entry of the list is empty it is not considered
            if None in vehicle:
                pass
            else:
                p.Vehicles.append(tuple(vehicle))
                p.Battery.append(tuple(battery))

        # Append new infrastructure types to the list and replace the values if this type is already in the list
        if infra[0] in infra_names:
            idx = infra_names.index(infra[0])
            p.Charging_Stations[idx] = infra
        else:
            if None in infra:
                pass
            else:
                p.Charging_Stations.append(infra)

    # Replace the other parameters if necessary or use the default values in case there is no data provided.
    p.project_duration = set_default_value(input_list[1][9], p.project_duration, "int", "project duration")
    p.inflation_rate = set_default_value(input_list[1][10], p.inflation_rate, "float", "inflation rate")
    p.interest_rate = set_default_value(input_list[1][11], p.interest_rate, "float", "interest rate")
    p.staff_cost = set_default_value(input_list[1][12], p.staff_cost, "float", "staff cost")
    p.fuel_cost = set_default_value(input_list[1][13], p.fuel_cost, "float", "fuel cost")
    p.maint_cost = set_default_value(input_list[1][14], p.maint_cost, "float", "maintenance cost")
    p.maint_infr_cost = set_default_value(input_list[1][15], p.maint_infr_cost, "float", "maintainance cost infrastructure")
    p.taxes = set_default_value(input_list[1][16], p.taxes, "float", "taxes")
    p.insurance = set_default_value(input_list[1][17], p.insurance, "float", "insurance")

    # Decide whether cost escalation is considered or not. The default procedure is to consider cost escalation.
    if input_list[0][17] == "" or input_list[1][18] == "TRUE":
        pass
    else:
        p.pef_fuel = p.pef_wages = p.pef_general = p.cef_vehicles = p.cef_battery = p.cef_infra = 0

    # Print a message for the user
    print("The CSV file has been read and your data is used in the TCO calculation. Please check the output file and verify your input data is correct.")


# Cast a value to the required datatype and return None in case of a ValueError
def cast_value(value, datatype):
    """
    This method casts the given value to the given datatype. If the cast is not possible due to a ValueError, None is returned.
    It is used in the read_csv method.

    :param value: The value to cast.
    :param datatype: The datatype which the value should be casted to.
    :return: The casted value.
    """
    if datatype == "int":
        try:
            value = int(value)
        except ValueError:
            value = None
    if datatype == "float":
        try:
            value = float(value)
        except ValueError:
            value = None
    return value


# Set the values in parameters.py to their default value and issue a warning in case there is no value provided.
def set_default_value(input_value, default_value, data_type, parameter_type):
    if cast_value(input_value, data_type) is None:
        w.warn("There was no value provided for the parameter {}. The default value {} is used.".format(parameter_type, default_value))
        return default_value
    else:
        return cast_value(input_value, data_type)



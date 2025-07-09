# This file contains methods used in the tco calculation and some additional methods

import json
import numpy as np
import warnings as w
import matplotlib.pyplot as plt
from matplotlib import colormaps as cm

import parameters as p



def net_present_value(
        cash_flow,
        years_after_base_year: int,
        discount_rate = 0.02
):
    """
    This method is used to calculate the net present value of any cash flow, a default value for the discount rate is set.

    :param cash_flow: The cashflow of which the present value needs to be calculated.
    :param years_after_base_year: The year after the base year in which the cashflow occurs.
    :param discount_rate: The discount rate by which the cash flow should be discounted.
    :return: A tuple of the present value of the cashflow rounded on 2 decimals and the year after base year in which the cashflow occurs.
    """
    npv = cash_flow / ((1 + discount_rate)**years_after_base_year)
    return npv, years_after_base_year


def annuity(
        procurement_cost: float,
        useful_life: int,
        interest_rate = 0.04
):
    """
    This method is used to calculate the annuity of an asset, a default value for the interest rate is set.

    :param procurement_cost: The procurement cost of the respective asset of which the annuty should be calculated.
    :param useful_life: The useful life of the respective asset, which is also the time over which the asset is financed.
    :param interest_rate: The interest rate which is the cost of the capital needed to procure the respective asset.
    :return: The value of the annuity rounded to 2 decimals.
    """
    ann = procurement_cost*interest_rate / (1-(1+interest_rate)**(-useful_life))
    return ann


def future_cost(
        cef,
        base_price,
        years_after_base_year
):
    """
    This method is used to calculate the costs of a certain category at a certain time taking into account the cost
    escalation factors (cef).

    :param cef: The cost escalation factor which represents the annual change of the costs / prices.
    :param base_price: The price in the base year.
    :param years_after_base_year: The years after the base year in which the cost arises.
    :return: The cost in the respective year and the year after the base year in which the cost arises.
    """
    cost = base_price * (1+cef)**years_after_base_year
    return cost, years_after_base_year


def replacement_cost(
        base_price,
        cost_escalation,
        useful_life,
        project_duration
):
    """
    In this method, the replacement costs of an asset are calculated considering the cost escalation.

    :param base_price: The price in the base year.
    :param cost_escalation: The cost escalation factor which represents the annual change of the costs / prices.
    :param useful_life: The useful life of the respective asset.
    :param project_duration: The duration of the project as a timeframe that is considered in this calculation.
    :return: The replacement cost as well as the number of years after the base year in which the replacement is
            conducted are returned with a binary variable which shows whether the useful life of the replaced asset is
            still within the project duration.
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


def total_proc_cef(
        procurement_cost: float,
        useful_life: int,
        project_duration: int,
        cost_escalation: float,
        interest_rate = 0.04,
        net_discount_rate = 0.02
):
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
    :return: The total procurement cost of the respective asset over the project duration considering the cost
            escalation and the present value
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


def calculate_total_driver_hours(
        driver_hours,
        annual_hours_per_driver = 1600,
        buffer = 0.1
):
    """
    This method calculates the total driver hours based on the number of drivers required for the operation of the buses.
    The buffer variable is the amount of hours added to the pure driving time and accounts for the time the drivers work
    but are not operating the bus.

    :param driver_hours: The amount of time the buses are operated by a driver.
    :param annual_hours_per_driver: The time a driver work over the course of one year.
    :param buffer: An additional factor which raises the total driver hours in order to account for any additional time
                    in which the bus is not operated but the driver is still working.
    :return: A tuple of the number of drivers and the total staff cost in one year.
    """
    # Integers are required, so // is used.
    number_drivers = (driver_hours*(1+buffer))//annual_hours_per_driver
    actual_driver_hours = annual_hours_per_driver * (number_drivers+1)
    return actual_driver_hours


# calculate the TCO
def tco_calculation(
        capex_input_dict,
        opex_input_dict,
        general_input_dict,
        save_result = False
):
    """
    This method is used to calculate the total cost of ownership based on the data provided through the three
    dictionaries.

    :param capex_input_dict: This dictionary contains all required input data to calculate the capex section of the TCO.
    :param opex_input_dict: This dictionary contains all required input data to calculate the opex section of the TCO.
    :param general_input_dict: This dictionary contains some general input parameters.
    :param save_result: Binary operator which determines, whether the result dictionary is directly saved to a json file.
    :return: A dictionary containing the specific tco by vehicle, the total TCO over the project duration,
             the annual TCO and the specific TCO over the project duration
    """
    result = {
        "tco_by_type": {}
    }


    # ----------Total CAPEX----------#

    total_capex = 0

    # Calculate the total cost for each asset over the project duration.
    for name, data in capex_input_dict.items():

        # Calculate the procurement cost for the respective asset including replacement.
        procurement_per_asset_type = total_proc_cef(data["procurement_cost"],
                                                    data["useful_life"],
                                                    general_input_dict["project_duration"],
                                                    data["cost_escalation"],
                                                    general_input_dict["interest_rate"],
                                                    general_input_dict["discount_rate"])
        # Add the cost of this asset to the CAPEX section of the TCO.
        total_capex += procurement_per_asset_type * data["number_of_assets"]
        # Add this cost component to the result dict for detailed analysis fo the tco
        result["tco_by_type"].update({
            name: (procurement_per_asset_type*data["number_of_assets"]
                   /(opex_input_dict["maint_cost_vehicles"].get("depending_on_scale")*general_input_dict.get("project_duration")))
        })

        # For vehicles, add the specific tco to the output dictionary.
        if data.get("annual_mileage") != None:
            # if this is the first entry, add the sepcific_tco_vehicles dictionary
            if result.get("specific_tco_vehicles") == None:
                result["specific_tco_vehicles"] = {
                name: round(((procurement_per_asset_type * data.get("number_of_assets"))/
                                (data.get("annual_mileage")*general_input_dict.get("project_duration"))),2)
            }
            # otherwise add the specific tco to the respective dictionary
            else:
                result["specific_tco_vehicles"].update({
                    name: round(((procurement_per_asset_type * data.get("number_of_assets"))/
                           (data.get("annual_mileage")*general_input_dict.get("project_duration"))),2)
                })

    # ----------Total OPEX----------#

    total_opex = 0

    # Calculate the OPEX for each category over the whole project duration.
    for name, data in opex_input_dict.items():

        total_opex_of_type=0

        # Calculate the OPEX for each year.
        for year in range(general_input_dict["project_duration"]):
            opex_cost_in_respective_year = future_cost(data["cost_escalation"], data["cost"], year)[0]*data["depending_on_scale"]
            total_opex_of_type += net_present_value(opex_cost_in_respective_year, year, general_input_dict["discount_rate"])[0]
        total_opex += total_opex_of_type

        # Save the total OPEX for each category in the result dictionary.
        result["tco_by_type"].update(
            {
                name: (total_opex_of_type/(opex_input_dict["maint_cost_vehicles"].get("depending_on_scale")*general_input_dict.get("project_duration")))
            }
        )

    # ----------Calculation of three kinds of TCO----------#

    # TCO over project duration
    result["TCO_over_PD"] = total_capex+total_opex

    # Annual TCO
    result["Annual_TCO"] = result["TCO_over_PD"]/general_input_dict["project_duration"]

    # Specific TCO over project duration
    result["Specific_TCO_over_PD"] = result["Annual_TCO"]/opex_input_dict["maint_cost_vehicles"]["depending_on_scale"]

    # save the mileage used to calculate the specific TCO
    result["Annual_fleet_mileage"] = general_input_dict["annual_fleet_mileage"]
    result["Annual_passenger_mileage"]=general_input_dict["passenger_mileage"]

    if save_result:
        with open("result_scenario_{}.json".format(str(general_input_dict["scenario"])),"w") as file:
            json.dump(result, file, indent = 4)

    return result


# Cast a value to the required datatype and return None in case of a ValueError
def cast_value(
        value,
        datatype
):
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
def set_default_value(
        input_value,
        default_value,
        data_type,
        parameter_type
):
    if cast_value(input_value, data_type) is None:
        w.warn("There was no value provided for the parameter {}. The default value {} is used.".format(parameter_type, default_value))
        return default_value
    else:
        return cast_value(input_value, data_type)

# get the input data from the input CSV file.
def read_json(
        jsonfile
):
    """
    This method reads the json file for the input data and changes the parameters in parameters.py to match the given
    values from the json file. If some values are not given, the default values from parameters.py are used instead.

    :param jsonfile: The json file which contains the input parameters.
    :return: None, this function purely changes the input parameters in parameters.py.
    """

    with open("input_tco.json", 'r') as f:
        # load data from the json file.
        input_dict = json.load(f)

    # Create lists with the names of vehicles, batteries and charging infrastructure in order to check, whether the
    # new entry needs to be appended to the list or a default value needs to be replaced

    # Add the tco data for the vehicles and batteries
    for key in input_dict["vehicles"].keys():
        # Only consider the entry if the key can be casted to an integer.
        try:
            # Make a list with the tco parameters and the vehicle id for each vehicle and append it to the respective
            # list in parameters.py.
            vehicle_data = [input_dict["vehicles"][key]["name"], # vehicle name
                            float(input_dict["vehicles"][key]["procurement_cost"]), # procurement cost
                            int(input_dict["vehicles"][key]["useful_life"]), # useful life
                            p.cef_vehicles] # cost escalation
                            #int(key)]  # vehicle id
            p.Vehicles.append(vehicle_data)
            # Repeat the same for each battery
            battery_data = [input_dict["vehicles"][key]["name"], # vehicle name
                            float(input_dict["vehicles"][key]["battery_procurement"]), # procurement cost
                            int(input_dict["vehicles"][key]["battery_useful_life"]), # useful life
                            p.cef_battery] # cost escalation
                            #int(key)] # vehicle id
            p.Battery.append(battery_data)
        except Exception:
            pass

    # Add the tco data for the infrastructure
    infra_names = [x[0] for x in p.Charging_Stations]
    for key in input_dict["infrastructure"].keys():
        # Only consider full dictionaries.
        try:
            infrastructure_data = [key,
                                   float(input_dict["infrastructure"][key]["procurement_cost"]),
                                   int(input_dict["infrastructure"][key]["useful_life"]),
                                   p.cef_infra]
            if key in infra_names:
                idx = infra_names.index(key)
                p.Charging_Stations[idx] = infrastructure_data
            else:
                p.Charging_Stations.append(infrastructure_data)
        except Exception:
            pass

    # Add the remaining tco parameters to the parameters.py file.

    # Replace the other parameters if necessary or use the default values in case there is no data provided.
    p.project_duration = set_default_value(
        input_dict["general_input"].get("Project_duration")[0],
        p.project_duration,
        "int",
        "project duration"
    )
    p.discount_rate = set_default_value(
        input_dict["general_input"].get("Discount_rate")[0]/100,
        p.discount_rate,
        "float",
        "discount rate")
    p.interest_rate = set_default_value(
        input_dict["general_input"].get("Interest_rate")[0]/100,
        p.interest_rate,
        "float",
        "interest rate")
    p.staff_cost = set_default_value(
        input_dict["general_input"].get("Staff_cost")[0],
        p.staff_cost,
        "float",
        "staff cost")
    p.fuel_cost = set_default_value(
        input_dict["general_input"].get("Fuel_cost")[0],
        p.fuel_cost,
        "float",
        "fuel cost")
    p.maint_cost = set_default_value(
        input_dict["general_input"].get("Maintenance_cost_vehicles")[0],
        p.maint_cost,
        "float",
        "maintenance cost")
    p.maint_infr_cost = set_default_value(
        input_dict["general_input"].get("Maintenance_cost_infrastructure")[0],
        p.maint_infr_cost,
        "float",
        "maintainance cost infrastructure")
    p.taxes = set_default_value(
        input_dict["general_input"].get("Taxes")[0],
        p.taxes,
        "float",
        "taxes")
    p.insurance = set_default_value(
        input_dict["general_input"].get("Insurance")[0],
        p.insurance,
        "float",
        "insurance")

    # Decide whether cost escalation is considered or not. The default procedure is to consider cost escalation.
    if (input_dict["general_input"]["Use_cost_escalation"]
            or input_dict["general_input"]["Use_cost_escalation"] == ""
            or input_dict["general_input"]["Use_cost_escalation"] == "TRUE"):
        pass
    else:
        p.cef_fuel = p.cef_wages = p.cef_general = p.cef_vehicles = p.cef_battery = p.cef_infra = 0

    # Print a message for the user
    print("The input file was loaded and your data is used in the TCO calculation. "
          "Please check the output file and verify your input data is correct.")



def tco_plot(result_dict, scenario_id):
    """
    This method plots the result of the specific tco in a bar chart in which the composition of the specific tco are highlighted.
    :param result_dict: The result dictionary as it is calculated in the tco_calculation method.
    :return: A plot of the tco.
    """
    # Make a list with all cost categories.
    tco_data = {
        "Infrastructure": 0,
        "Vehicle": 0,
        "Battery": 0,
        "Other Cost": (result_dict["tco_by_type"]["insurance"]+result_dict["tco_by_type"]["taxes"]),
        "Vehicle Maintenance Cost": result_dict["tco_by_type"]["maint_cost_vehicles"],
        "Infrastructure Maintenance Cost": result_dict["tco_by_type"]["maint_cost_infra"],"Staff Cost": result_dict["tco_by_type"]["staff_cost"],
        "Energy Cost": result_dict["tco_by_type"]["fuel_cost"]
    }
    for name, data in result_dict["tco_by_type"].items():
        if "INFRASTRUCTURE" in name:
            tco_data["Infrastructure"] += data
        elif "VEHICLE" in name:
            tco_data["Vehicle"] += data
        elif "BATTERY" in name:
            tco_data["Battery"] += data

    # Create a figure with fixed size.
    Fig = plt.figure(1, (5,8))
    ax = Fig.add_subplot(1, 1, 1)

    # Use colormaps to choose the colors for the plot
    color = cm.get_cmap('managua')(np.linspace(0,1,len(tco_data.keys())))

    # Bottom of the stacked bars.
    bottom = 0
    # Create the stacked bar plot
    for color, [tco_categories, data] in zip(color, tco_data.items()):
        p = ax.bar('specific TCO', data, width = 0.05, label=tco_categories, bottom=bottom, color=color)
        bottom += data
        ax.bar_label(p, labels=[f'{data:.2f}' if data != 0 else ''], label_type='center', padding=3, size=12)

    # write the total tco over the bar
    ax.text(0, (bottom+0.1),s = str("{:.2f}".format(round(bottom,2))), ha = 'center', va = 'bottom', fontweight = 'bold', size = 12)

    # Set limit on y axis
    ax.set_ylim(top = bottom+0.5)
    # set title
    ax.set_title('Specific Total Cost of Ownership in Scenario {}'.format(str(scenario_id)))
    # set the y-axis label
    ax.set_ylabel('TCO in €/km')

    ax.legend(bbox_to_anchor=(0.5, -0.05), loc='upper center', ncol = 2)
    plt.tight_layout()
    plt.show()
    Fig.savefig("tco_plot_scn_{}.png".format(scenario_id))
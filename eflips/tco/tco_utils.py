# This file contains methods used in the tco calculation and some additional methods

from dataclasses import dataclass
import csv, json

import matplotlib.pyplot as plt
from matplotlib import colormaps as cm
import numpy as np

import warnings as w

from enum import Enum, auto



def net_present_value(cash_flow, years_after_base_year: int, discount_rate=0.02):
    """
    This method is used to calculate the net present value of any cash flow, a default value for the discount rate is set.

    :param cash_flow: The cashflow of which the present value needs to be calculated.
    :param years_after_base_year: The year after the base year in which the cashflow occurs.
    :param discount_rate: The discount rate by which the cash flow should be discounted.
    :return: A tuple of the present value of the cashflow rounded on 2 decimals and the year after base year in which the cashflow occurs.
    """
    npv = cash_flow / ((1 + discount_rate) ** years_after_base_year)
    return npv


def annuity(procurement_cost: float, useful_life: int, interest_rate=0.04):
    """
    This method is used to calculate the annuity of an asset, a default value for the interest rate is set.

    :param procurement_cost: The procurement cost of the respective asset of which the annuty should be calculated.
    :param useful_life: The useful life of the respective asset, which is also the time over which the asset is financed.
    :param interest_rate: The interest rate which is the cost of the capital needed to procure the respective asset.
    :return: The value of the annuity rounded to 2 decimals.
    """
    ann = procurement_cost * interest_rate / (1 - (1 + interest_rate) ** (-useful_life))
    return ann


def future_cost(cef, base_price, years_after_base_year):
    """
    This method is used to calculate the costs of a certain category at a certain time taking into account the cost
    escalation factors (cef).

    :param cef: The cost escalation factor which represents the annual change of the costs / prices.
    :param base_price: The price in the base year.
    :param years_after_base_year: The years after the base year in which the cost arises.
    :return: The cost in the respective year and the year after the base year in which the cost arises.
    """
    cost = base_price * (1 + cef) ** years_after_base_year
    return cost, years_after_base_year


def replacement_cost(base_price, cost_escalation, useful_life, project_duration):
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
    for i in range(number_of_full_replacements + 1):
        # The new price is the baseprice multiplied by the cost escalation factor to the power of the years after the base year.
        new_price = base_price * (1 + cost_escalation) ** (i * useful_life)
        # If the project ends before the useful life if the next replacement, the binary variable is set true in order
        # to account for that in the total_proc_cef function.
        years_used = (i + 1) * useful_life
        if years_used <= project_duration:
            replacement.append((new_price, (i * useful_life), False))
            if years_used == project_duration:
                break
        else:
            # The useful life is shorter than the remaining project duration
            replacement.append((new_price, (i * useful_life), True))
            break
    return replacement



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
        "Other Cost": (
            result_dict["tco_by_type"]["insurance"]
            + result_dict["tco_by_type"]["taxes"]
        ),
        "Vehicle Maintenance Cost": result_dict["tco_by_type"]["maint_cost_vehicles"],
        "Infrastructure Maintenance Cost": result_dict["tco_by_type"][
            "maint_cost_infra"
        ],
        "Staff Cost": result_dict["tco_by_type"]["staff_cost"],
        "Energy Cost": result_dict["tco_by_type"]["fuel_cost"],
    }
    for name, data in result_dict["tco_by_type"].items():
        if "INFRASTRUCTURE" in name:
            tco_data["Infrastructure"] += data
        elif "VEHICLE" in name:
            tco_data["Vehicle"] += data
        elif "BATTERY" in name:
            tco_data["Battery"] += data

    # Create a figure with fixed size.
    Fig = plt.figure(1, (5, 8))
    ax = Fig.add_subplot(1, 1, 1)

    # Use colormaps to choose the colors for the plot
    color = cm.get_cmap("managua")(np.linspace(0, 1, len(tco_data.keys())))

    # Bottom of the stacked bars.
    bottom = 0
    # Create the stacked bar plot
    for color, [tco_categories, data] in zip(color, tco_data.items()):
        p = ax.bar(
            "specific TCO",
            data,
            width=0.05,
            label=tco_categories,
            bottom=bottom,
            color=color,
        )
        bottom += data
        ax.bar_label(p, label_type="center", padding=3, fmt="%.2f")

    # write the total tco over the bar
    ax.text(
        0,
        (bottom + 0.1),
        s=str("{:.2f}".format(round(bottom, 2))),
        ha="center",
        va="bottom",
        fontweight="bold",
    )

    # Set limit on y axis
    ax.set_ylim(top=bottom + 0.5)
    # set title
    ax.set_title(
        "Specific Total Cost of Ownership in Scenario {}".format(str(scenario_id))
    )
    # set the y-axis label
    ax.set_ylabel("TCO in €/km")

    ax.legend(bbox_to_anchor=(0.5, -0.05), loc="upper center", ncol=2)
    plt.tight_layout()
    # plt.show()
    Fig.savefig("tco_plot_scn_{}.png".format(scenario_id))

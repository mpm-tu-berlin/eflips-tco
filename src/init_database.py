# This script initialises the database at the beginning of the TCO calculation.
# The input parameters are added into the tco_parameter section for the VehicleType,

from eflips.model import VehicleType, Scenario, BatteryType, ChargingPointType
import parameters as p

def init_database(session, scenario):
    # Add the missing data for VehicleType and BatteryType
    all_vtypes = session.query(
        VehicleType
    ).filter(
        VehicleType.scenario_id == scenario.id
    ).all()
    for vtype in all_vtypes:
        tco_parameters = {
            "name": vtype.name,
            "procurement_cost": p.vehicle_dict().get(vtype.name, {}).get("procurement_cost"),
            "useful_life": p.vehicle_dict().get(vtype.name, {}).get("useful_life"),
            "cost_escalation": p.vehicle_dict().get(vtype.name, {}).get("cost_escalation")
        }
        # Only change the database if the same input Parameters are not already in it.
        if vtype.tco_parameters == tco_parameters:
            pass
        else:
            vtype.tco_parameters = tco_parameters

        #### Add the missing data for BatteryType ####

        # Get the battery-TCO parameters for the considered vehicle:
        tco_parameters_battery = {
            "name": vtype.name,
            "procurement_cost": p.battery_dict().get(vtype.name, {}).get("procurement_cost"),
            "useful_life": p.battery_dict().get(vtype.name, {}).get("useful_life"),
            "cost_escalation": p.battery_dict().get(vtype.name, {}).get("cost_escalation")
        }
        # if there already is a battery type linked to the vehicle, the tco parameters are simply added to this battery type.
        if vtype.battery_type_id is not None:
            battery_type = session.query(
                BatteryType
            ).filter(
                 BatteryType.id == vtype.battery_type_id
            ).first()
            #if battery_type.tco_parameters != tco_parameters_battery:
            battery_type.tco_parameters = tco_parameters_battery
            session.flush()
        # if there is no battery type, it needs to be added.
        else:
            # create new battery type which will be added to the BatteryType table
            new_battery_type = BatteryType(scenario_id= vtype.scenario_id, specific_mass= 1, chemistry = "xyz", tco_parameters = tco_parameters_battery)
            session.add(new_battery_type)
            session.flush()
            vtype.battery_type_id = new_battery_type.id

            # Link the new battery type to the respective vehicle type.
            #battery_type = session.query(
            #    BatteryType
            #).filter(
            #    BatteryType.scenario_id == vtype.scenario_id,
            #    BatteryType.tco_parameters == tco_parameters_battery
            #).first()
            #vtype.battery_type_id = battery_type.id

    #### Next, the tco_parameters for the charging infrastructure is added ####

    # First the charging stations are considered
    # Depot charging Stations

    # Add charging point types:
    new_charge_point_120 = ChargingPointType(scenario_id = scenario.id, name = "120 kw_Slot", name_short = "120")
    new_charge_point_300 = ChargingPointType(scenario_id = scenario.id, name = "300 kw_Slot", name_short = "300")
    session.add_all([new_charge_point_120, new_charge_point_300])

    charging_points = session.query(
        ChargingPointType
    ).filter(
        ChargingPointType.scenario_id == scenario.id
    ).all()

    for chp in charging_points:
        # Add the tco_parameters to the charging points (slots)
        tco_parameters_charging_point = {
            "name": chp.name,
            "procurement_cost": p.charging_stations_dict().get(chp.name, {}).get("procurement_cost"),
            "useful_life": p.charging_stations_dict().get(chp.name, {}).get("useful_life"),
            "cost_escalation": p.charging_stations_dict().get(chp.name, {}).get("cost_escalation")
        }
        chp.tco_parameters =  tco_parameters_charging_point
    session.commit()



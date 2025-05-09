# This script initialises the database at the beginning of the TCO calculation.
# The input parameters are added into the tco_parameter section for the VehicleType,

from eflips.model import VehicleType, Scenario, BatteryType, ChargingPointType, Process, AssocAreaProcess, Area, Depot, Station
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

    #### Next, the tco_parameters for the charging infrastructure is added ####

    #--------Depot charging Stations--------#

    # Add charging point types only if they are not yet included in the database
    Charging_Points = session.query(ChargingPointType).all()
    Slot_120 = Slot_300 = True
    for cp in Charging_Points:
        if cp.name == "120 kw_Slot": Slot_120 = False
        if cp.name == "300 kw_Slot": Slot_300 = False
    if Slot_120:
        new_charge_point_120 = ChargingPointType(scenario_id=scenario.id, name="120 kw_Slot", name_short="120")
        session.add(new_charge_point_120)
    if Slot_300:
        new_charge_point_300 = ChargingPointType(scenario_id = scenario.id, name = "300 kw_Slot", name_short = "300")
        session.add(new_charge_point_300)

    # Get the charging point types from the DB to add the tco_parameters
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
    session.flush()

    # Next, the charging_point_id needs to be added into "Area" for all depot charging slots
    all_electrified_areas = session.query(
        Area
    ).join(
        AssocAreaProcess, AssocAreaProcess.area_id == Area.id
    ).join(
        Process, AssocAreaProcess.process_id == Process.id
    ).filter(
        Area.scenario_id == scenario.id,
        Process.electric_power is not None
    ).all()

    # get the ChargingPointType.id which is suitable for the depot charging.
    cpt_id = session.query(
        ChargingPointType.id
    ).filter(
        ChargingPointType.scenario_id == scenario.id,
        ChargingPointType.name_short == "120"
    ).scalar()
    # Write the charging_point_type_id into all areas
    for area in all_electrified_areas:
        area.charging_point_type_id = cpt_id

    # The tco_parameters for the depot charging stations are added to the Station table
    tco_parameters_dc = {
        "name": "DEPOT Station",
        "procurement_cost": p.charging_stations_dict().get("DEPOT Station", {}).get("procurement_cost"),
        "useful_life": p.charging_stations_dict().get("DEPOT Station", {}).get("useful_life"),
        "cost_escalation": p.charging_stations_dict().get("DEPOT Station", {}).get("cost_escalation")
    }

    # to do this, the Depots must be excluded from the Stations
    dc_stations = session.query(
        Station
    ).join(
        Depot, Station.id == Depot.station_id
    ).filter(
        Station.is_electrified == True,
        Station.scenario_id == scenario.id
    ).all()
    # Then the tco_parameters for the depot charging stations are added to stations.
    for station in dc_stations:
        # Add the tco parameters for the OC station
        if station.tco_parameters != tco_parameters_dc:
            station.tco_parameters = tco_parameters_dc



    #--------Opportunity Charging--------#

    # Next, the charging_point_type_id needs to be added to the Station table for all opportunity charging
    # get the id of the OC charging Slots
    cpt_id = session.query(
        ChargingPointType.id
    ).filter(
        ChargingPointType.scenario_id == scenario.id,
        ChargingPointType.name_short == "300"
    ).scalar()

    # Get the procurement cost of an Opportunity charging station:
    tco_parameters_oc = {
        "name": "OPPORTUNITY Station",
        "procurement_cost": p.charging_stations_dict().get("OPPORTUNITY Station", {}).get("procurement_cost"),
        "useful_life": p.charging_stations_dict().get("OPPORTUNITY Station", {}).get("useful_life"),
        "cost_escalation": p.charging_stations_dict().get("OPPORTUNITY Station", {}).get("cost_escalation")
    }

    # to do this, the Depots must be excluded from the Stations
    # TODO reevaluate query
    # it can also by filtered by the charge_type which is depb or oppb
    oc_stations = session.query(
        Station
    ).outerjoin(
        Depot, Station.id == Depot.station_id
    ).filter(
        Station.is_electrified == True,
        Station.scenario_id == scenario.id,
        Depot.station_id == None
    ).all()

    for station in oc_stations:
        # Add the charging_point_type_id
        if station.charging_point_type_id != cpt_id:
            station.charging_point_type_id = cpt_id
        # Add the tco parameters for the OC station
        if station.tco_parameters != tco_parameters_oc:
            station.tco_parameters = tco_parameters_oc
    session.commit()

    # TODO optimize the initialization to make it more robust.



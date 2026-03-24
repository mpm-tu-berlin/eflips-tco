"""TCO parameter defaults for different scenarios.

Usage:
    from eflips.tco.default_params import get_params, get_default_params

    # Load from a file path (usable from any package)
    params = get_params("/path/to/my_scenario.py")

    # Load a built-in default scenario
    params = get_default_params("berlin")

    vehicle_types = params.VEHICLE_TYPES
    scenario_tco = params.SCENARIO_TCO
"""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Dict, Union

from . import berlin_bvg, berlin_literature

SCENARIOS: Dict[str, ModuleType] = {
    "berlin": berlin_bvg,
    "berlin_literature": berlin_literature,
}


def get_params_from_file(path: Union[str, Path]) -> ModuleType:
    """Load TCO parameters from a Python file.

    The file should define module-level variables: VEHICLE_TYPES, BATTERY_TYPES,
    CHARGING_POINT_TYPES, CHARGING_INFRASTRUCTURE, and SCENARIO_TCO.

    Args:
        path: Path to a Python file containing TCO parameter definitions.

    Returns:
        Module containing the parameter variables.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Parameter file not found: {path}")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_default_params(scenario_name: str) -> ModuleType:
    """Get the defaults module for a scenario.

    Args:
        scenario_name: Name of the scenario (e.g., "berlin")

    Returns:
        Module containing VEHICLE_TYPES, BATTERY_TYPES, CHARGING_POINT_TYPES,
        CHARGING_INFRASTRUCTURE, and SCENARIO_TCO.

    Raises:
        KeyError: If scenario_name is not found.
    """
    if scenario_name not in SCENARIOS:
        available = ", ".join(SCENARIOS.keys())
        raise KeyError(f"Unknown scenario '{scenario_name}'. Available: {available}")
    return SCENARIOS[scenario_name]


def list_scenarios() -> list[str]:
    """List available scenario names."""
    return list(SCENARIOS.keys())

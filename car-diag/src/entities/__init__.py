"""Entity layer: domain models and core logic.

This layer has no external dependencies. All classes are immutable
frozen dataclasses or enumerations.
"""

from src.entities.connection_state import ConnectionState
from src.entities.dtc import DTC, DtcCategory, decode_obd2_dtc, decode_uds_dtc
from src.entities.ecu import DiagProtocolType, EcuInfo
from src.entities.pid import PidDefinition, STANDARD_PIDS
from src.entities.did import DidDefinition
from src.entities.vehicle_parameter import VehicleParameter

__all__ = [
    "ConnectionState",
    "DTC",
    "DtcCategory",
    "decode_obd2_dtc",
    "decode_uds_dtc",
    "DiagProtocolType",
    "EcuInfo",
    "PidDefinition",
    "STANDARD_PIDS",
    "DidDefinition",
    "VehicleParameter",
]

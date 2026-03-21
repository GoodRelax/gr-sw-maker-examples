"""JsonDtcDatabase: DtcDescriptionProvider Protocol の内蔵辞書実装.

主要な OBD-II DTC の英語説明文を内蔵辞書として搭載する。

traces: FR-06b, LIM-01
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# P0001 - P0499 の主要 DTC 説明文 (SAE J2012 準拠)
# LIM-01: 汎用 OBD-II コード (P0xxx) のみ対応
_BUILTIN_DTC_DESCRIPTIONS: dict[str, str] = {
    # Fuel and Air Metering
    "P0001": "Fuel Volume Regulator Control Circuit/Open",
    "P0002": "Fuel Volume Regulator Control Circuit Range/Performance",
    "P0003": "Fuel Volume Regulator Control Circuit Low",
    "P0004": "Fuel Volume Regulator Control Circuit High",
    "P0010": "A Camshaft Position Actuator Circuit (Bank 1)",
    "P0011": "A Camshaft Position - Timing Over-Advanced or System Performance (Bank 1)",
    "P0012": "A Camshaft Position - Timing Over-Retarded (Bank 1)",
    "P0013": "B Camshaft Position - Actuator Circuit (Bank 1)",
    "P0014": "B Camshaft Position - Timing Over-Advanced or System Performance (Bank 1)",
    "P0015": "B Camshaft Position - Timing Over-Retarded (Bank 1)",
    "P0016": "Crankshaft Position - Camshaft Position Correlation (Bank 1 Sensor A)",
    "P0017": "Crankshaft Position - Camshaft Position Correlation (Bank 1 Sensor B)",
    "P0020": "A Camshaft Position Actuator Circuit (Bank 2)",
    "P0021": "A Camshaft Position - Timing Over-Advanced or System Performance (Bank 2)",
    "P0022": "A Camshaft Position - Timing Over-Retarded (Bank 2)",
    "P0030": "HO2S Heater Control Circuit (Bank 1 Sensor 1)",
    "P0031": "HO2S Heater Control Circuit Low (Bank 1 Sensor 1)",
    "P0032": "HO2S Heater Control Circuit High (Bank 1 Sensor 1)",
    "P0036": "HO2S Heater Control Circuit (Bank 1 Sensor 2)",
    "P0037": "HO2S Heater Control Circuit Low (Bank 1 Sensor 2)",
    "P0038": "HO2S Heater Control Circuit High (Bank 1 Sensor 2)",
    # Fuel System
    "P0068": "MAP/MAF - Throttle Position Correlation",
    "P0069": "Manifold Absolute Pressure - Barometric Pressure Correlation",
    "P0087": "Fuel Rail/System Pressure - Too Low",
    "P0088": "Fuel Rail/System Pressure - Too High",
    "P0089": "Fuel Pressure Regulator 1 Performance",
    # Engine Misfire
    "P0100": "Mass or Volume Air Flow Circuit Malfunction",
    "P0101": "Mass or Volume Air Flow Circuit Range/Performance Problem",
    "P0102": "Mass or Volume Air Flow Circuit Low Input",
    "P0103": "Mass or Volume Air Flow Circuit High Input",
    "P0104": "Mass or Volume Air Flow Circuit Intermittent",
    "P0105": "Manifold Absolute Pressure/Barometric Pressure Circuit Malfunction",
    "P0106": "Manifold Absolute Pressure/Barometric Pressure Circuit Range/Performance Problem",
    "P0107": "Manifold Absolute Pressure/Barometric Pressure Circuit Low Input",
    "P0108": "Manifold Absolute Pressure/Barometric Pressure Circuit High Input",
    "P0110": "Intake Air Temperature Circuit Malfunction",
    "P0111": "Intake Air Temperature Circuit Range/Performance Problem",
    "P0112": "Intake Air Temperature Circuit Low Input",
    "P0113": "Intake Air Temperature Circuit High Input",
    "P0115": "Engine Coolant Temperature Circuit Malfunction",
    "P0116": "Engine Coolant Temperature Circuit Range/Performance Problem",
    "P0117": "Engine Coolant Temperature Circuit Low Input",
    "P0118": "Engine Coolant Temperature Circuit High Input",
    "P0120": "Throttle/Pedal Position Sensor/Switch A Circuit Malfunction",
    "P0121": "Throttle/Pedal Position Sensor/Switch A Circuit Range/Performance Problem",
    "P0122": "Throttle/Pedal Position Sensor/Switch A Circuit Low Input",
    "P0123": "Throttle/Pedal Position Sensor/Switch A Circuit High Input",
    "P0125": "Insufficient Coolant Temperature for Closed Loop Fuel Control",
    "P0128": "Coolant Thermostat (Coolant Temperature Below Thermostat Regulating Temperature)",
    "P0130": "O2 Sensor Circuit Malfunction (Bank 1 Sensor 1)",
    "P0131": "O2 Sensor Circuit Low Voltage (Bank 1 Sensor 1)",
    "P0132": "O2 Sensor Circuit High Voltage (Bank 1 Sensor 1)",
    "P0133": "O2 Sensor Circuit Slow Response (Bank 1 Sensor 1)",
    "P0134": "O2 Sensor Circuit No Activity Detected (Bank 1 Sensor 1)",
    "P0135": "O2 Sensor Heater Circuit Malfunction (Bank 1 Sensor 1)",
    "P0136": "O2 Sensor Circuit Malfunction (Bank 1 Sensor 2)",
    "P0137": "O2 Sensor Circuit Low Voltage (Bank 1 Sensor 2)",
    "P0138": "O2 Sensor Circuit High Voltage (Bank 1 Sensor 2)",
    "P0139": "O2 Sensor Circuit Slow Response (Bank 1 Sensor 2)",
    "P0140": "O2 Sensor Circuit No Activity Detected (Bank 1 Sensor 2)",
    "P0141": "O2 Sensor Heater Circuit Malfunction (Bank 1 Sensor 2)",
    "P0143": "O2 Sensor Circuit Low Voltage (Bank 1 Sensor 3)",
    "P0150": "O2 Sensor Circuit Malfunction (Bank 2 Sensor 1)",
    "P0151": "O2 Sensor Circuit Low Voltage (Bank 2 Sensor 1)",
    "P0152": "O2 Sensor Circuit High Voltage (Bank 2 Sensor 1)",
    "P0153": "O2 Sensor Circuit Slow Response (Bank 2 Sensor 1)",
    "P0154": "O2 Sensor Circuit No Activity Detected (Bank 2 Sensor 1)",
    "P0155": "O2 Sensor Heater Circuit Malfunction (Bank 2 Sensor 1)",
    "P0170": "Fuel Trim Malfunction (Bank 1)",
    "P0171": "System Too Lean (Bank 1)",
    "P0172": "System Too Rich (Bank 1)",
    "P0174": "System Too Lean (Bank 2)",
    "P0175": "System Too Rich (Bank 2)",
    # Ignition System
    "P0200": "Injector Circuit Malfunction",
    "P0201": "Injector Circuit Malfunction - Cylinder 1",
    "P0202": "Injector Circuit Malfunction - Cylinder 2",
    "P0203": "Injector Circuit Malfunction - Cylinder 3",
    "P0204": "Injector Circuit Malfunction - Cylinder 4",
    "P0205": "Injector Circuit Malfunction - Cylinder 5",
    "P0206": "Injector Circuit Malfunction - Cylinder 6",
    "P0217": "Engine Overtemp Condition",
    "P0218": "Transmission Over Temperature Condition",
    "P0219": "Engine Overspeed Condition",
    "P0220": "Throttle/Pedal Position Sensor/Switch B Circuit Malfunction",
    "P0221": "Throttle/Pedal Position Sensor/Switch B Circuit Range/Performance Problem",
    "P0222": "Throttle/Pedal Position Sensor/Switch B Circuit Low Input",
    "P0223": "Throttle/Pedal Position Sensor/Switch B Circuit High Input",
    # Emission Controls
    "P0300": "Random/Multiple Cylinder Misfire Detected",
    "P0301": "Cylinder 1 Misfire Detected",
    "P0302": "Cylinder 2 Misfire Detected",
    "P0303": "Cylinder 3 Misfire Detected",
    "P0304": "Cylinder 4 Misfire Detected",
    "P0305": "Cylinder 5 Misfire Detected",
    "P0306": "Cylinder 6 Misfire Detected",
    "P0307": "Cylinder 7 Misfire Detected",
    "P0308": "Cylinder 8 Misfire Detected",
    "P0325": "Knock Sensor 1 Circuit Malfunction (Bank 1 or Single Sensor)",
    "P0327": "Knock Sensor 1 Circuit Low Input (Bank 1 or Single Sensor)",
    "P0328": "Knock Sensor 1 Circuit High Input (Bank 1 or Single Sensor)",
    "P0335": "Crankshaft Position Sensor A Circuit Malfunction",
    "P0336": "Crankshaft Position Sensor A Circuit Range/Performance",
    "P0340": "Camshaft Position Sensor Circuit Malfunction",
    "P0341": "Camshaft Position Sensor Circuit Range/Performance",
    "P0351": "Ignition Coil A Primary/Secondary Circuit Malfunction",
    "P0352": "Ignition Coil B Primary/Secondary Circuit Malfunction",
    "P0353": "Ignition Coil C Primary/Secondary Circuit Malfunction",
    "P0354": "Ignition Coil D Primary/Secondary Circuit Malfunction",
    # Auxiliary Emissions Controls
    "P0400": "Exhaust Gas Recirculation Flow Malfunction",
    "P0401": "Exhaust Gas Recirculation Flow Insufficient Detected",
    "P0402": "Exhaust Gas Recirculation Flow Excessive Detected",
    "P0403": "Exhaust Gas Recirculation Circuit Malfunction",
    "P0410": "Secondary Air Injection System Malfunction",
    "P0411": "Secondary Air Injection System Incorrect Flow Detected",
    "P0420": "Catalyst System Efficiency Below Threshold (Bank 1)",
    "P0421": "Warm Up Catalyst Efficiency Below Threshold (Bank 1)",
    "P0430": "Catalyst System Efficiency Below Threshold (Bank 2)",
    "P0440": "Evaporative Emission Control System Malfunction",
    "P0441": "Evaporative Emission Control System Incorrect Purge Flow",
    "P0442": "Evaporative Emission Control System Leak Detected (small leak)",
    "P0443": "Evaporative Emission Control System Purge Control Valve Circuit Malfunction",
    "P0446": "Evaporative Emission Control System Vent Control Circuit Malfunction",
    "P0449": "Evaporative Emission Control System Vent Valve/Solenoid Circuit Malfunction",
    "P0450": "Evaporative Emission Control System Pressure Sensor Malfunction",
    "P0451": "Evaporative Emission Control System Pressure Sensor Range/Performance",
    "P0452": "Evaporative Emission Control System Pressure Sensor Low Input",
    "P0453": "Evaporative Emission Control System Pressure Sensor High Input",
    "P0455": "Evaporative Emission Control System Leak Detected (gross leak)",
    "P0456": "Evaporative Emission Control System Leak Detected (very small leak)",
    "P0460": "Fuel Level Sensor Circuit Malfunction",
    "P0461": "Fuel Level Sensor Circuit Range/Performance",
    "P0462": "Fuel Level Sensor Circuit Low Input",
    "P0463": "Fuel Level Sensor Circuit High Input",
    "P0480": "Cooling Fan 1 Control Circuit Malfunction",
    "P0481": "Cooling Fan 2 Control Circuit Malfunction",
    "P0496": "Evaporative Emission System High Purge Flow",
    "P0497": "Evaporative Emission System Low Purge Flow",
    "P0498": "Evaporative Emission System Vent Valve Control Circuit Low",
    "P0499": "Evaporative Emission System Vent Valve Control Circuit High",
    # Speed/Idle Control
    "P0500": "Vehicle Speed Sensor Malfunction",
    "P0501": "Vehicle Speed Sensor Range/Performance",
    "P0505": "Idle Control System Malfunction",
    "P0506": "Idle Control System RPM Lower Than Expected",
    "P0507": "Idle Control System RPM Higher Than Expected",
    # Transmission
    "P0700": "Transmission Control System Malfunction",
    "P0715": "Input/Turbine Speed Sensor Circuit Malfunction",
    "P0720": "Output Speed Sensor Circuit Malfunction",
    "P0725": "Engine Speed Input Circuit Malfunction",
    "P0730": "Incorrect Gear Ratio",
    "P0740": "Torque Converter Clutch Circuit Malfunction",
    "P0741": "Torque Converter Clutch Circuit Performance or Stuck Off",
    "P0750": "Shift Solenoid A Malfunction",
    "P0755": "Shift Solenoid B Malfunction",
    "P0760": "Shift Solenoid C Malfunction",
    "P0765": "Shift Solenoid D Malfunction",
}


class JsonDtcDatabase:
    """DTC 説明文検索の内蔵辞書実装.

    主要な OBD-II DTC (P0001-P0499 等) の英語説明文を内蔵辞書として保持する。
    メーカー固有コード (P1xxx 等) は "Unknown" を返す。

    traces: FR-06b, LIM-01
    """

    def __init__(
        self,
        additional_descriptions: dict[str, str] | None = None,
    ) -> None:
        """JsonDtcDatabase を初期化する.

        Args:
            additional_descriptions: 追加の DTC 説明文辞書。
                内蔵辞書に存在しない DTC を追加する場合に使用する。
        """
        self._descriptions: dict[str, str] = dict(_BUILTIN_DTC_DESCRIPTIONS)
        if additional_descriptions:
            self._descriptions.update(additional_descriptions)

        logger.info(
            "DTC database initialized",
            extra={"dtc_count": len(self._descriptions)},
        )

    def lookup(self, dtc_code: str) -> str:
        """DTC コードに対応する説明文を返す.

        UDS DTC コード (例: "P0143-07") の場合はサフィックスを除去して検索する。

        Args:
            dtc_code: DTC コード文字列 (例: "P0143", "P0143-07").

        Returns:
            英語説明文。該当なしの場合は "Unknown".

        traces: FR-06b, FR-06e
        """
        # UDS DTC のサフィックス (-XX) を除去して基本コードで検索
        base_code = dtc_code.split("-")[0].upper()

        description = self._descriptions.get(base_code, "Unknown")

        if description == "Unknown":
            logger.debug(
                "DTC description not found",
                extra={"dtc_code": dtc_code, "base_code": base_code},
            )

        return description

    @property
    def dtc_count(self) -> int:
        """登録されている DTC 説明文の総数を返す."""
        return len(self._descriptions)

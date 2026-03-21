"""ConnectionState: FR-02 FSA の全 11 状態と有効遷移マッピング.

traces: FR-02, FR-02a, FR-02b, FR-02c, FR-02d
"""

from __future__ import annotations

from enum import StrEnum


class ConnectionState(StrEnum):
    """ELM327 接続の有限状態機械（FSA）状態.

    FR-02 で定義された 11 状態を列挙する。
    """

    S_DISCONNECTED = "S_DISCONNECTED"
    S_CONNECTING = "S_CONNECTING"
    S_CONNECTED = "S_CONNECTED"
    S_ECU_SCANNING = "S_ECU_SCANNING"
    S_DID_SCANNING = "S_DID_SCANNING"
    S_DTC_READING = "S_DTC_READING"
    S_DTC_CLEARING = "S_DTC_CLEARING"
    S_MONITORING = "S_MONITORING"
    S_RECORDING = "S_RECORDING"
    S_PROTOCOL_SWITCHING = "S_PROTOCOL_SWITCHING"
    S_ERROR = "S_ERROR"


# FR-02 状態遷移規則に基づく有効な遷移マッピング。
# 通信断（comm loss）は全状態から S_DISCONNECTED への遷移を含む（FR-02a）。
VALID_TRANSITIONS: dict[ConnectionState, frozenset[ConnectionState]] = {
    ConnectionState.S_DISCONNECTED: frozenset({
        ConnectionState.S_CONNECTING,
    }),
    ConnectionState.S_CONNECTING: frozenset({
        ConnectionState.S_CONNECTED,
        ConnectionState.S_ERROR,
        ConnectionState.S_DISCONNECTED,  # comm loss
    }),
    ConnectionState.S_CONNECTED: frozenset({
        ConnectionState.S_ECU_SCANNING,
        ConnectionState.S_DID_SCANNING,
        ConnectionState.S_DTC_READING,
        ConnectionState.S_DTC_CLEARING,
        ConnectionState.S_MONITORING,
        ConnectionState.S_RECORDING,
        ConnectionState.S_DISCONNECTED,  # user disconnect or comm loss
    }),
    ConnectionState.S_ECU_SCANNING: frozenset({
        ConnectionState.S_CONNECTED,       # scan completed or user abort
        ConnectionState.S_DISCONNECTED,    # comm loss
    }),
    ConnectionState.S_DID_SCANNING: frozenset({
        ConnectionState.S_CONNECTED,       # scan completed or user abort
        ConnectionState.S_DISCONNECTED,    # comm loss (with cache save)
    }),
    ConnectionState.S_DTC_READING: frozenset({
        ConnectionState.S_CONNECTED,           # read completed
        ConnectionState.S_PROTOCOL_SWITCHING,  # KWP ECU detected
        ConnectionState.S_DISCONNECTED,        # comm loss
    }),
    ConnectionState.S_DTC_CLEARING: frozenset({
        ConnectionState.S_CONNECTED,           # clear completed
        ConnectionState.S_PROTOCOL_SWITCHING,  # KWP ECU detected
        ConnectionState.S_DISCONNECTED,        # comm loss
    }),
    ConnectionState.S_MONITORING: frozenset({
        ConnectionState.S_CONNECTED,     # user stops dashboard
        ConnectionState.S_RECORDING,     # user starts recording
        ConnectionState.S_DISCONNECTED,  # comm loss
    }),
    ConnectionState.S_RECORDING: frozenset({
        ConnectionState.S_MONITORING,    # user stops recording
        ConnectionState.S_CONNECTED,     # user stops dashboard
        ConnectionState.S_DISCONNECTED,  # comm loss (with TSV flush)
    }),
    ConnectionState.S_PROTOCOL_SWITCHING: frozenset({
        ConnectionState.S_DTC_READING,    # switch for read
        ConnectionState.S_DTC_CLEARING,   # switch for clear
        ConnectionState.S_ECU_SCANNING,   # switch for scan
        ConnectionState.S_CONNECTED,      # switch completed standalone
        ConnectionState.S_DISCONNECTED,   # comm loss
    }),
    ConnectionState.S_ERROR: frozenset({
        ConnectionState.S_DISCONNECTED,  # user acknowledges error or comm loss
    }),
}


def is_valid_transition(
    current_state: ConnectionState,
    next_state: ConnectionState,
) -> bool:
    """指定された状態遷移が有効かを判定する.

    Args:
        current_state: 現在の状態.
        next_state: 遷移先の状態.

    Returns:
        遷移が有効であれば True.
    """
    allowed = VALID_TRANSITIONS.get(current_state, frozenset())
    return next_state in allowed

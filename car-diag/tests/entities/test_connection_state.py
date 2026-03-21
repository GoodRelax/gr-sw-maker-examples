"""ConnectionState エンティティのテスト.

FSA 状態定義と遷移規則の正当性を検証する。
"""

from __future__ import annotations

import pytest

from src.entities.connection_state import (
    VALID_TRANSITIONS,
    ConnectionState,
    is_valid_transition,
)


class TestConnectionState:
    """ConnectionState 列挙のテスト."""

    def test_state_count(self) -> None:
        """FR-02: 11 状態が定義されている."""
        assert len(ConnectionState) == 11

    def test_initial_state_is_disconnected(self) -> None:
        """初期状態は S_DISCONNECTED."""
        assert ConnectionState.S_DISCONNECTED == "S_DISCONNECTED"

    def test_all_states_have_transition_rules(self) -> None:
        """全状態に遷移規則が定義されている."""
        for state in ConnectionState:
            assert state in VALID_TRANSITIONS, (
                f"State {state} has no transition rules"
            )


class TestValidTransitions:
    """状態遷移規則のテスト."""

    def test_disconnected_can_connect(self) -> None:
        """S_DISCONNECTED -> S_CONNECTING は有効."""
        assert is_valid_transition(
            ConnectionState.S_DISCONNECTED,
            ConnectionState.S_CONNECTING,
        )

    def test_disconnected_cannot_monitor(self) -> None:
        """S_DISCONNECTED -> S_MONITORING は無効."""
        assert not is_valid_transition(
            ConnectionState.S_DISCONNECTED,
            ConnectionState.S_MONITORING,
        )

    def test_connecting_to_connected(self) -> None:
        """S_CONNECTING -> S_CONNECTED は有効."""
        assert is_valid_transition(
            ConnectionState.S_CONNECTING,
            ConnectionState.S_CONNECTED,
        )

    def test_connecting_to_error(self) -> None:
        """S_CONNECTING -> S_ERROR は有効."""
        assert is_valid_transition(
            ConnectionState.S_CONNECTING,
            ConnectionState.S_ERROR,
        )

    def test_connected_to_all_operations(self) -> None:
        """S_CONNECTED から各操作状態への遷移が有効."""
        operations = [
            ConnectionState.S_ECU_SCANNING,
            ConnectionState.S_DID_SCANNING,
            ConnectionState.S_DTC_READING,
            ConnectionState.S_DTC_CLEARING,
            ConnectionState.S_MONITORING,
            ConnectionState.S_RECORDING,
            ConnectionState.S_DISCONNECTED,
        ]
        for target in operations:
            assert is_valid_transition(
                ConnectionState.S_CONNECTED,
                target,
            ), f"S_CONNECTED -> {target} should be valid"

    def test_monitoring_to_recording(self) -> None:
        """S_MONITORING -> S_RECORDING は有効."""
        assert is_valid_transition(
            ConnectionState.S_MONITORING,
            ConnectionState.S_RECORDING,
        )

    def test_recording_to_monitoring(self) -> None:
        """S_RECORDING -> S_MONITORING は有効."""
        assert is_valid_transition(
            ConnectionState.S_RECORDING,
            ConnectionState.S_MONITORING,
        )

    def test_error_to_disconnected(self) -> None:
        """S_ERROR -> S_DISCONNECTED は有効."""
        assert is_valid_transition(
            ConnectionState.S_ERROR,
            ConnectionState.S_DISCONNECTED,
        )

    def test_error_cannot_connect_directly(self) -> None:
        """S_ERROR -> S_CONNECTING は無効（一旦 S_DISCONNECTED を経由する）."""
        assert not is_valid_transition(
            ConnectionState.S_ERROR,
            ConnectionState.S_CONNECTING,
        )


class TestCommLossTransitions:
    """FR-02a: 全状態からの通信断（comm loss）遷移テスト."""

    def test_all_states_can_reach_disconnected(self) -> None:
        """全状態から S_DISCONNECTED への遷移が可能.

        S_DISCONNECTED 自身を除く全状態からの comm loss ハンドリング。
        """
        for state in ConnectionState:
            if state == ConnectionState.S_DISCONNECTED:
                continue
            assert is_valid_transition(
                state,
                ConnectionState.S_DISCONNECTED,
            ), f"{state} -> S_DISCONNECTED should be valid (comm loss)"

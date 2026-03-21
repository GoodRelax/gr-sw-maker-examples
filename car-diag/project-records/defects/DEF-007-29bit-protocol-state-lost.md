# DEF-007: ECU スキャン後にプロトコル状態が ATSP0 に戻り DTC 読取・ダッシュボードが動作しない

<!-- common_block:
  file_type: defect-report
  project: car-diag
  language: ja
  owner: implementer
  status: fixed
-->

<!-- form_block:
  defect:
    defect_id: DEF-007
    severity: Critical
    priority: Critical
    phase_detected: testing（実機動作確認）
    phase_injected: implementation（CR-002 統合時）
    category: state-management
    parent_cr: CR-002
    related_requirements:
      - FR-06（DTC 取得）
      - FR-08（車両データダッシュボード）
      - FR-03（ECU 自動スキャン）
-->

## 現象

1. ECU スキャン後に DTC 読取すると全 ECU で 0 件（PoC では多数検出済み）
2. ダッシュボードのモニタリング開始後、パラメータが表示されない

## 根本原因

CR-002 で追加した全 PA スキャン (Phase 2) は ATSP7 + ATCP18 を設定するが、スキャン完了時に `ATSP0`（自動検出）に戻していた。その後の DTC 読取・ダッシュボードポーリングでは `_set_can_header(ecu.ecu_identifier)` のみを呼び、**29bit CAN に必要な ATSP7 + ATCP18 + ATSH DA xx F1 のプロトコル設定を行わない**ため、全コマンドが NO DATA になった。

## 修正内容

`_prepare_ecu_communication(ecu)` メソッドを新規追加:

- ECU の `ecu_identifier` が `18DA_xx` 形式なら ATSP7 + ATCP18 + ATSH DA xx F1 を設定
- それ以外（11bit CAN 等）なら従来通り ATSP6 + ATSH を設定

以下の 6 箇所で `_set_can_header(ecu.ecu_identifier)` を `_prepare_ecu_communication(ecu)` に置換:

- `_read_dtcs_uds()`
- `_read_dtcs_legacy_obd()`
- `_clear_dtcs_uds()`
- `_read_did_uds()`
- `_read_pid()`
- `scan_dids()` (DID スキャン)

## テスト結果

145 テスト全 PASS

## 教訓

- CR-002 の影響分析で「DTC 読取・ダッシュボードへの影響」を検出すべきだった
- 29bit CAN はプロトコル設定が必要という知見が、スキャン実装以外の箇所に横展開されていなかった
- プロトコル状態を暗黙的に管理するのではなく、各操作の先頭で明示的に設定する方式に改善

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "defect 票作成・修正完了"
-->

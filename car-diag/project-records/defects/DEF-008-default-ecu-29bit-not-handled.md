# DEF-008: デフォルト ECU で 29bit CAN 車両のダッシュボードが動作しない

<!-- common_block:
  file_type: defect-report
  project: car-diag
  language: ja
  owner: implementer
  status: fixed
-->

<!-- form_block:
  defect:
    defect_id: DEF-008
    severity: High
    priority: High
    phase_detected: testing（実機動作確認）
    phase_injected: implementation（DEF-007 修正時）
    category: regression
    parent_defect: DEF-007
    related_requirements:
      - FR-08（車両データダッシュボード）
-->

## 現象

ECU スキャンせずにダッシュボードのモニタリングを開始すると、パラメータが表示されない。

## 根本原因

DEF-007 の修正で `_prepare_ecu_communication()` を追加したが、デフォルト ECU（`ecu_identifier="DEFAULT"`）の場合、`"DEFAULT".startswith("18DA_")` が `False` → `_ensure_can_protocol()` → ATSP6（11bit CAN）に切替 → 29bit CAN 車両では応答なし。

接続時に 29bit CAN であることは PID 検出応答（`18 DA F1 0E ...`）から判定可能だったが、その情報を保持していなかった。

## 修正内容

1. `__init__` に `_is_29bit_can: bool` フラグを追加
2. `detect_supported_pids()` で最初の `0100` 応答に `18 DA` が含まれていたら `_is_29bit_can = True` に設定
3. `_prepare_ecu_communication()` で `DEFAULT` ECU かつ `_is_29bit_can` の場合、ATSP0（自動検出）を維持しヘッダ設定なしで送信

## テスト結果

145 テスト全 PASS

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "defect 票作成・修正完了"
-->

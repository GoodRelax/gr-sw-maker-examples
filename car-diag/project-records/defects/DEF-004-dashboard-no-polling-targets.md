# DEF-004: ダッシュボードにポーリングターゲットが渡されず表示が空

<!-- common_block:
  file_type: defect-report
  project: car-diag
  language: ja
  owner: implementer
  status: fixed
-->

<!-- form_block:
  defect:
    defect_id: DEF-004
    severity: High
    priority: High
    phase_detected: testing（実機動作確認）
    phase_injected: implementation
    category: integration
    related_requirements:
      - FR-04（車両データダッシュボード）
    related_review: review-impl-20260321.md (M-04)
-->

## 現象

PID 検出で 17 個の PID を検出済みにもかかわらず、ダッシュボードのモニタリング開始時に `Polling targets built: target_count=0` となり、何もグラフ表示されない。

## 根本原因

`_start_monitoring_polling()` 内の `build_polling_targets()` 呼び出しで `legacy_obd_ecu` 引数が省略されていた（デフォルト `None`）。`build_polling_targets()` は `legacy_obd_ecu` が `None` の場合、PID ターゲットを生成しない設計のため、ターゲット 0 個となった。

レビュー M-04（GUI-UseCase 未接続）で指摘されていた問題の一部。

## 修正内容

`src/main.py` の `_start_monitoring_polling()`:

- `detected_ecu_list` から `DiagProtocolType.LEGACY_OBD` の ECU を探索
- `build_polling_targets()` に `legacy_obd_ecu=obd_ecu` として渡す
- `DiagProtocolType` の import を追加

## テスト結果

145 テスト全 PASS

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "defect 票作成・修正完了"
-->

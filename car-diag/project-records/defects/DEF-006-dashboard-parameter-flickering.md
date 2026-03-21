# DEF-006: ダッシュボードのパラメータが増減を繰り返す（フリッカー）

<!-- common_block:
  file_type: defect-report
  project: car-diag
  language: ja
  owner: implementer
  status: fixed
-->

<!-- form_block:
  defect:
    defect_id: DEF-006
    severity: Medium
    priority: High
    phase_detected: testing（実機動作確認）
    phase_injected: implementation
    category: usability
    related_requirements:
      - FR-04（車両データダッシュボード）
      - NFR-03（ユーザビリティ）
-->

## 現象

ダッシュボード監視中にパラメータが表示されたり消えたりを繰り返す。

## 根本原因

`poll_once()` で PID 読取がタイムアウトまたはエラーになった場合、結果リストに含めずスキップ (`continue`) していた。UI は毎回結果リスト全体で表示を更新するため、一時的に応答がなかった PID は画面から消え、次のポーリングで成功すると再出現する。

## 修正内容

`src/use_cases/monitor_dashboard.py`:

- `_last_readings: dict[str, VehicleParameter]` を追加し、成功時に前回値を保存
- 読取失敗時は前回値をフォールバックとして結果リストに含める
- これにより一度検出されたパラメータは、通信断まで安定して表示される

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "defect 票作成・修正完了"
-->

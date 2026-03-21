# DEF-001: ECUスキャンとダッシュボード監視のシリアルポート競合

<!-- common_block:
  file_type: defect-report
  project: car-diag
  language: ja
  owner: implementer
  status: fixed
-->

<!-- form_block:
  defect:
    defect_id: DEF-001
    severity: High
    priority: High
    phase_detected: testing（実機動作確認）
    phase_injected: implementation
    category: race-condition
    related_requirements:
      - FR-06（ECU 自動スキャン）
      - FR-04（車両データダッシュボード）
      - FR-09（接続状態管理 FSA）
    related_review: review-impl-20260321.md (M-04)
-->

## 現象

ECU スキャン実行時に `Serial write failed` / `Serial port is not open` エラーが連続発生し、スキャンが失敗する。

## 再現手順

1. ELM327 に接続する
2. ダッシュボードタブで監視を開始する（ポーリング中）
3. 接続タブで「ECU スキャン」を押す
4. シリアルポートへの同時アクセスが衝突し、エラーが発生する

## 根本原因

`_on_scan_ecu_requested()` がダッシュボードのポーリングを停止せずに ECU スキャンを開始していた。ELM327 はシングルスレッドの AT コマンドインターフェースであり、同時に複数のコマンドを受け付けられない。ダッシュボードのポーリングタイマーが PID リクエストを送信している最中に、ECU スキャンがプロトコル切替コマンド（`ATSP5` 等）を送信し、通信が破壊された。

## 修正内容

`src/main.py` の `_on_scan_ecu_requested()` を修正:

- ECU スキャン開始前に `monitor_use_case.is_monitoring()` を確認
- 監視中であれば `_stop_monitoring_polling()` でポーリングを一時停止
- スキャン完了後のコールバック内で `_start_monitoring_polling()` を呼びポーリングを自動再開

## 影響範囲

- `src/main.py`: `_on_scan_ecu_requested()` 関数
- 同様のパターンが DID スキャン・DTC 取得でも発生しうる（要確認）

## 横展開確認

| 操作 | シリアル排他制御 | 状態 |
|------|-----------------|------|
| ECU スキャン | 修正済み（DEF-001） | fixed |
| DID スキャン | 要確認 | pending |
| DTC 取得 | 要確認 | pending |
| DTC 消去 | 要確認 | pending |

## 教訓

シングルチャネルのシリアル通信デバイスを扱う場合、全ての操作でシリアルポートの排他制御を保証する設計パターン（コマンドキュー or ミューテックス）を適用すべきだった。

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "defect 票作成・修正完了"
-->

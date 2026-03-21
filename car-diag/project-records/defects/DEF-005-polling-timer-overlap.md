# DEF-005: ダッシュボードポーリングの QTimer が重複発火しシリアル通信崩壊

<!-- common_block:
  file_type: defect-report
  project: car-diag
  language: ja
  owner: implementer
  status: fixed
-->

<!-- form_block:
  defect:
    defect_id: DEF-005
    severity: Critical
    priority: Critical
    phase_detected: testing（実機動作確認）
    phase_injected: implementation
    category: concurrency
    related_requirements:
      - FR-04（車両データダッシュボード）
      - FR-09（接続状態管理 FSA）
    related_defects:
      - DEF-001（シリアルポート排他制御の欠如）
-->

## 現象

ダッシュボード監視開始後、コンソールに `Command sent` が連続で表示され `Response received` が追いつかない。応答がバイナリゴミ（`\x00\x00...`）になり、全ての PID 値が `Invalid response discarded` としてドロップされる。画面には何も表示されない。

## 根本原因

QTimer（500ms 間隔）が `_poll_dashboard()` を発火するたびにワーカースレッドで `poll_once()` を起動していたが、前回のポーリング（全 PID 読取）が 500ms 以内に完了しない場合、新しいワーカーが並行起動される。複数のワーカーが同時にシリアルポートへコマンドを送信し、ELM327 のバッファが溢れて通信が崩壊した。

DEF-001 と同根の問題（シリアルポートの排他制御不足）。

## 修正内容

`src/main.py` の `_poll_dashboard()` に排他制御フラグ `polling_in_progress` を追加:

- ポーリング開始時に `True` に設定、完了コールバック/エラーコールバックで `False` に戻す
- `True` の間は QTimer の発火をスキップし、前回完了後に次のポーリングを許可する

## テスト結果

145 テスト全 PASS

## 教訓

- ELM327 はシングルスレッドの AT コマンドインターフェース。全操作でコマンドキュー or 排他フラグが必須
- DEF-001 の教訓（シリアルポート排他制御）が横展開されていなかった
- QTimer + ワーカースレッドのパターンでは、ワーカーの実行時間がタイマー間隔を超える場合の考慮が必要

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "defect 票作成・修正完了"
-->

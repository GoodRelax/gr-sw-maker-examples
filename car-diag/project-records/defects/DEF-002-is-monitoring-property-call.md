# DEF-002: is_monitoring プロパティをメソッド呼び出しした TypeError

<!-- common_block:
  file_type: defect-report
  project: car-diag
  language: ja
  owner: implementer
  status: fixed
-->

<!-- form_block:
  defect:
    defect_id: DEF-002
    severity: High
    priority: High
    phase_detected: testing（実機動作確認）
    phase_injected: implementation（DEF-001 修正時）
    category: regression
    parent_defect: DEF-001
    related_requirements:
      - FR-06（ECU 自動スキャン）
-->

## 現象

ECU スキャンボタン押下時に `TypeError: 'bool' object is not callable` が発生し、スキャンが実行されない。

## 根本原因

DEF-001 の修正で `monitor_use_case.is_monitoring()` と記述したが、`is_monitoring` は `@property` デコレータ付きのプロパティであり、メソッドではない。括弧 `()` を付けたことで、戻り値の `bool` オブジェクトを関数として呼び出そうとし TypeError が発生した。

## 修正内容

`src/main.py` L320:

- 修正前: `was_monitoring = monitor_use_case.is_monitoring()`
- 修正後: `was_monitoring = monitor_use_case.is_monitoring`

## 教訓

- defect 修正時にも既存コードの API（プロパティ vs メソッド）を確認すること
- regression を防ぐため、修正後に最低限の動作確認（起動→接続→スキャン操作）を行うこと
- DEF-001 の修正が手動だったためレビュー・テストを経ずにリリースされた。hotfix であっても既存テストの実行を省略しない

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "defect 票作成・修正完了"
-->

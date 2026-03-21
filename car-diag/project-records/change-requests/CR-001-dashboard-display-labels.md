# CR-001: ダッシュボードにパラメータ名・SID/PID・ECU名を表示

<!-- common_block:
  file_type: change-request
  project: car-diag
  language: ja
  owner: change-manager
  status: approved
-->

<!-- form_block:
  change_request:
    cr_id: CR-001
    requester: user
    request_date: "2026-03-21"
    impact_level: Low
    decision_status: approved
    approved_date: "2026-03-21"
    related_requirements:
      - FR-04（車両データダッシュボード）
      - NFR-03（ユーザビリティ）
-->

## 変更要求内容

ダッシュボードのパラメータ表示を改善する:

1. パラメータ列にPID hex コードだけでなく、パラメータ名を併記する
   - 例: `04` → `04: Calculated Engine Load`
2. ECU列にECU識別子だけでなく、ECU表示名を使用する
   - 例: `DEFAULT` → `ECU_18DA_0E`

## 変更理由

PID hex コードのみでは何のパラメータか即座に判断できず、ユーザビリティが低い（マジックナンバー状態）。

## 影響分析

| 影響対象 | 影響内容 | 影響度 |
|----------|----------|--------|
| FR-04 | 表示フォーマットの追加仕様 | Low |
| src/main.py | `on_poll_finished` の表示変換ロジック追加 | Low |
| GUI テーブル列幅 | パラメータ名が長くなるため列幅調整が必要な可能性 | Low |
| TSV ヘッダ | 現時点では PID hex のまま（変更なし） | なし |
| グラフ凡例 | パラメータ名が反映される | Low |

## 仕様書への反映

FR-04 に以下の要件を追加:

- FR-04e: ダッシュボードのパラメータ表示は PID/DID コードとパラメータ名を併記すること
- FR-04f: ECU 列には ECU 表示名を使用すること

## 実装状況

実装済み:

- `src/main.py`: `on_poll_finished` 内の表示変換ロジック
- `src/framework/gui/dashboard_tab.py`: パラメータ名の長さに合わせた列幅調整（パラメータ名 250px、値 120px、単位 60px、ECU 伸縮）

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "change-manager"
    changes: "CR 作成・影響分析・承認・実装済み"
-->

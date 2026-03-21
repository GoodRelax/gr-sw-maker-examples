# WBS (Work Breakdown Structure) — car-diag

## ガントチャート概要

```mermaid
gantt
    title car-diag 開発スケジュール
    dateFormat YYYY-MM-DD
    axisFormat %m/%d

    section Phase 0-1 企画
    条件付きプロセス評価       :done, p0, 2026-03-21, 1d
    CLAUDE.md 作成             :done, p0b, 2026-03-21, 1d
    インタビュー               :done, p1a, 2026-03-21, 1d
    仕様書 Ch1-2               :done, p1b, 2026-03-21, 1d
    仕様書レビュー R1          :done, p1c, 2026-03-21, 1d

    section Phase 2 外部依存
    HW要求仕様                 :done, p2a, 2026-03-21, 1d
    ADR記録                    :done, p2b, 2026-03-21, 1d

    section Phase 3 設計
    Ch3-6 詳細化               :done, p3a, 2026-03-21, 1d
    セキュリティ設計           :active, p3b, 2026-03-21, 1d
    可観測性設計               :done, p3c, 2026-03-21, 1d
    WBS作成                    :active, p3d, 2026-03-21, 1d
    リスク台帳                 :active, p3e, 2026-03-21, 1d
    設計レビュー R2/R4/R5      :active, p3f, 2026-03-21, 1d

    section Phase 4 実装
    Entity層                   :p4a, after p3f, 2d
    UseCase層                  :p4b, after p4a, 3d
    Adapter層                  :p4c, after p4a, 3d
    Framework層 シリアル通信   :p4d, after p4c, 2d
    Framework層 GUI            :p4e, after p4b, 4d
    単体テスト                 :p4f, after p4b, 3d
    実装レビュー               :p4g, after p4f, 1d

    section Phase 5 テスト
    結合テスト                 :p5a, after p4g, 2d
    GUIテスト                  :p5b, after p4g, 2d
    テストレビュー             :p5c, after p5b, 1d

    section Phase 6 納品
    PyInstaller パッケージング :p6a, after p5c, 1d
    日本語マニュアル           :p6b, after p5c, 2d
    最終レビュー               :p6c, after p6b, 1d
    完了報告                   :p6d, after p6c, 1d
```

## WBS テーブル

| WBS# | タスク | 担当 | 依存 | ステータス |
|------|--------|------|------|-----------|
| 0.1 | 条件付きプロセス評価 | orchestrator | - | 完了 |
| 0.2 | CLAUDE.md 作成 | orchestrator | 0.1 | 完了 |
| 1.1 | インタビュー | srs-writer | 0.2 | 完了 |
| 1.2 | 仕様書 Ch1-2 | srs-writer | 1.1 | 完了 |
| 1.3 | 仕様書レビュー R1 | review-agent | 1.2 | 完了 (PASS) |
| 2.1 | HW 要求仕様 | architect | 1.3 | 完了 |
| 2.2 | ADR 記録 | architect | 2.1 | 完了 |
| 3.1 | Ch3-6 詳細化 | architect | 1.3 | 完了 |
| 3.2 | セキュリティ設計 | security-reviewer | 3.1 | 進行中 |
| 3.3 | 可観測性設計 | architect | 3.1 | 完了 |
| 3.4 | WBS 作成 | progress-monitor | 3.1 | 進行中 |
| 3.5 | リスク台帳 | risk-manager | 3.1 | 進行中 |
| 3.6 | 設計レビュー R2/R4/R5 | review-agent | 3.1 | 進行中 |
| 4.1 | Entity 層実装 | implementer | 3.6 | 未着手 |
| 4.2 | Use Case 層実装 | implementer | 4.1 | 未着手 |
| 4.3 | Adapter 層実装 | implementer | 4.1 | 未着手 |
| 4.4 | Framework 層（シリアル通信） | implementer | 4.3 | 未着手 |
| 4.5 | Framework 層（GUI） | implementer | 4.2 | 未着手 |
| 4.6 | 単体テスト | test-engineer | 4.2 | 未着手 |
| 4.7 | 実装レビュー R2/R3/R4/R5 | review-agent | 4.6 | 未着手 |
| 4.8 | SCA スキャン | security-reviewer | 4.7 | 未着手 |
| 4.9 | ライセンス確認 | license-checker | 4.7 | 未着手 |
| 5.1 | 結合テスト | test-engineer | 4.7 | 未着手 |
| 5.2 | GUI テスト | test-engineer | 4.7 | 未着手 |
| 5.3 | テストレビュー R6 | review-agent | 5.2 | 未着手 |
| 6.1 | PyInstaller パッケージング | implementer | 5.3 | 未着手 |
| 6.2 | 日本語マニュアル | user-manual-writer | 5.3 | 未着手 |
| 6.3 | 最終レビュー R1-R6 | review-agent | 6.2 | 未着手 |
| 6.4 | 完了報告 | orchestrator | 6.3 | 未着手 |

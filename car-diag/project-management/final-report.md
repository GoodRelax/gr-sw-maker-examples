# car-diag 最終レポート

- date: 2026-03-21
- project: car-diag
- method: full-auto-dev (gr-sw-maker)

---

## 1. プロジェクト概要

ELM327 Bluetooth OBD ドングルを使用して車両の診断・データログ取得を行う Windows 11 デスクトップアプリケーション。

### 主要機能

| # | 機能 | 状態 |
|---|------|------|
| 1 | ELM327 接続管理（COM ポート経由） | 実装完了 |
| 2 | 接続状態管理（FSA: 11状態） | 実装完了 |
| 3 | ECU 自動スキャン（CAN + KWP） | 実装完了 |
| 4 | スキャン結果キャッシュ（VIN キー、90日自動削除） | 実装完了 |
| 5 | DID スキャン（プリセット + 全スキャン、中断・再開） | 実装完了 |
| 6 | DTC 取得（Legacy OBD / UDS / KWP2000 マルチプロトコル） | 実装完了 |
| 7 | DTC 消去（マルチプロトコル） | 実装完了 |
| 8 | 車両データダッシュボード（リアルタイムグラフ） | 実装完了 |
| 9 | データ記録（TSV、500ms 間隔、fsync 1秒） | 実装完了 |

### 技術スタック

| 項目 | 技術 |
|------|------|
| 言語 | Python 3.12+ |
| GUI | PyQt6 |
| シリアル通信 | pyserial |
| リアルタイムグラフ | pyqtgraph |
| テスト | pytest / pytest-qt / pytest-cov |
| パッケージング | PyInstaller |
| アーキテクチャ | Clean Architecture (4層) |

---

## 2. 品質メトリクス

### テスト結果

| 指標 | 目標 | 実績 | 判定 |
|------|------|------|------|
| 単体テスト合格率 | 95%以上 | **100%** (141/141) | PASS |
| ビジネスロジックカバレッジ | 80%以上 | **95%+** (Entity + Use Case) | PASS |
| Critical/High レビュー指摘 | 0件 | **0件** | PASS |

### レビュー実績

| レビュー | 対象 | 結果 |
|---------|------|------|
| review-001 | 仕様書 Ch1-2 (R1) | FAIL → 修正 |
| review-002 | 仕様書 Ch1-2 再レビュー (R1) | **PASS** |
| review-003 | 仕様書 Ch3-4 (R2/R4/R5) | **PASS** |
| review-004 | 実装コード (R2/R3/R4/R5) | **PASS** |

### リスク管理

| ID | リスク | スコア | 状態 |
|----|--------|--------|------|
| RSK-01 | ELM327 クローンチップの互換性 | 6 | オープン (LIM-02 で許容) |
| RSK-02 | DID 全スキャンの速度 | 4 | オープン (中断・再開で対応) |
| RSK-03 | KWP2000 プロトコル切替失敗 | 2 | オープン |
| RSK-04 | PyInstaller アンチウイルス誤検知 | 3 | オープン |
| RSK-05 | リアルタイムグラフの描画性能 | 4 | 対応済 (600点上限) |

---

## 3. 成果物一覧

### 仕様・設計文書

| ファイル | 内容 |
|---------|------|
| docs/spec/car-diag-spec.md | ANMS 仕様書 (Ch1-6) |
| docs/hw-requirement-spec.md | ELM327 HW 要求仕様 |
| docs/api/openapi.yaml | OpenAPI 3.0 仕様 |
| docs/security/security-design.md | セキュリティ設計 |
| docs/observability/observability-design.md | 可観測性設計 |
| docs/user-manual.md | 日本語ユーザーマニュアル |

### ソースコード

| ディレクトリ | ファイル数 | 内容 |
|-------------|-----------|------|
| src/entities/ | 7 | ドメインモデル (DTC, PID, DID, ECU, VehicleParameter, ConnectionState) |
| src/use_cases/ | 9 | ビジネスロジック (接続, スキャン, DTC, ダッシュボード, 記録, キャッシュ) |
| src/adapters/ | 3 | ELM327Adapter, ScanCacheRepository, DtcDatabase |
| src/framework/ | 9 | シリアルポート, TSVライタ, ログ設定, GUI (7タブ/ダイアログ) |
| src/main.py | 1 | エントリポイント + DI コンテナ |

### テストコード

| ディレクトリ | テスト数 |
|-------------|---------|
| tests/entities/ | 50 |
| tests/use_cases/ | 42 |
| tests/adapters/ | 33 |
| tests/framework/ | 13 |
| tests/ (root) | 3 |
| **合計** | **141** |

### プロセス記録

| ファイル | 内容 |
|---------|------|
| project-management/interview-record.md | インタビュー記録 |
| project-management/progress/wbs.md | WBS・ガントチャート |
| project-records/decisions/adr-001-*.md | ELM327 HW 選定 ADR |
| project-records/decisions/adr-002-*.md | ライセンス確認 ADR |
| project-records/risks/risk-register.md | リスク台帳 |
| project-records/reviews/*.md | レビュー報告 (4件) |

---

## 4. 既知の制限事項

1. ELM327 実機テスト未実施（モックベースのテストのみ）
2. PyInstaller exe 化は未実施（Phase 6 残作業）
3. GUI テストは PyQt6 インストール環境でのみ実行可能
4. メーカー固有 DTC (P1xxx 等) の説明文は「Unknown」と表示

---

## 5. 次のステップ（ユーザーアクション）

1. **ELM327 実機テスト**: ELM327 ドングルを車に接続し、実車での動作確認
2. **PyInstaller パッケージング**: `pyinstaller --onefile src/main.py` で exe 化
3. **フィードバック**: 実車テスト結果に基づく改善要望があれば change-manager 経由で対応

# CR-002: ECU スキャンを 29bit CAN 全 PA スキャンに拡張

<!-- common_block:
  file_type: change-request
  project: car-diag
  language: ja
  owner: change-manager
  status: approved
-->

<!-- form_block:
  change_request:
    cr_id: CR-002
    requester: user
    request_date: "2026-03-21"
    impact_level: High
    decision_status: approved
    approved_date: "2026-03-21"
    related_requirements:
      - FR-06（ECU 自動スキャン）
      - FR-01（ELM327 接続管理）
    related_poc: poc/poc-report-29bit-can.md
-->

## 変更要求内容

ECU スキャンを以下の 3 フェーズ構成に変更する:

1. **Phase 1**: CAN ブロードキャスト `0100`（既存 + ウォームアップ兼用）
2. **Phase 2**: 29bit CAN 物理アドレス全スキャン (0x00-0xFF) — TesterPresent ($3E00) を 2 段階タイムアウトで送信
   - 高速パス: ATST20 (128ms)
   - リトライ: ATSTFF (1020ms)
3. **Phase 3**: KWP スキャン（既存、クローン非対応時はスキップ）

## 変更理由

PoC 検証（poc/poc-report-29bit-can.md）で以下が判明:

- ファンクショナルアドレスでは OBD-II 対応 ECU (0x0E) しか検出できない
- ゲートウェイ裏の ECU (0x30, 0x60) は物理アドレスでのみ到達可能
- TesterPresent が全 ECU で確実に応答する
- 2 段階タイムアウトで約 1〜2 分に短縮可能

## 影響分析

| 影響対象 | 影響内容 | 影響度 |
|----------|----------|--------|
| FR-06 | スキャン方式の根本変更（ブロードキャストのみ → 全 PA スキャン追加） | High |
| src/adapters/elm327_adapter.py | `scan_ecus()` 全面改修、`_probe_29bit_tester_present()` 新規追加、`_finish_scan()` 新規追加 | High |
| _CAN_ECU_NAMES | 29bit CAN 物理アドレスの ECU 名マッピング追加 | Low |
| スキャン所要時間 | 数秒 → 約 1〜2 分に増加 | Medium |
| GUI | 進捗表示が 256 ステップ分に拡大 | Low |

## 仕様書への反映

FR-06 に以下を追加:

- FR-06g: The System shall 29bit CAN 物理アドレス (0x00-0xFF) に TesterPresent ($3E00) を送信し、応答した ECU を検出する。高速パス (ATST20: 128ms) で全アドレスをスキャン後、未検出アドレスを拡張タイムアウト (ATSTFF: 1020ms) でリトライする.
- FR-06h: The System shall スキャン開始前に CAN バスウォームアップ（ファンクショナル 0100 送信）を実行し、CAN バス接続を確立する.

## 実装状況

実装済み:

- `src/adapters/elm327_adapter.py`: `scan_ecus()` 3 フェーズ化、`_probe_29bit_tester_present()` 追加、`_finish_scan()` 追加、`_CAN_ECU_NAMES` 29bit 対応
- テスト: 145 テスト全 PASS

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "change-manager"
    changes: "CR 作成・影響分析・承認・実装済み"
-->

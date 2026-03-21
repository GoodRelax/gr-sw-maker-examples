# DEF-003: 29bit CAN アドレス未対応 + クローン ELM327 で ECU 検出不可

<!-- common_block:
  file_type: defect-report
  project: car-diag
  language: ja
  owner: implementer
  status: fixed
-->

<!-- form_block:
  defect:
    defect_id: DEF-003
    severity: Critical
    priority: Critical
    phase_detected: testing（実機動作確認）
    phase_injected: implementation
    category: compatibility
    related_requirements:
      - FR-01c（PID 検出）
      - FR-06（ECU 自動スキャン）
      - HWR-11（応答パース）
      - CON-01（ELM327 クローン品の存在）
-->

## 現象

1. 接続成功するが Supported PIDs が 0 個と報告される
2. ECU スキャンで全 ECU が NO DATA となり 0 個検出

## 根本原因

### 原因1: 29bit CAN アドレスの応答をパースできない

車両が ISO 15765-4 CAN 29bit アドレッシングで応答した場合、ヘッダが `18 DA F1 0E` のように 4 バイト（スペース区切り4トークン）になる。`_parse_obd_response()` は 11bit CAN（3桁1トークン: `7E8`）しか想定しておらず、29bit ヘッダをデータバイトとして誤解釈していた。

実際の応答: `'SEARCHING...\r18 DA F1 0E 06 41 00 XX XX XX XX \r\r'`（データ部マスク済み）
期待パース: ヘッダ `18 DA F1 0E` + DL `06` + データ `41 00 XX XX XX XX`
実際パース: `18` をデータ先頭と解釈 → SID `0x18` != expected `0x41` → None

### 原因2: クローン ELM327 v1.5 が UDS TesterPresent に未対応

ECU プローブに UDS TesterPresent (`3E 00`) を使用していたが、クローン ELM327 v1.5 チップは UDS サービスを正しくルーティングできず、全 ECU で `NO DATA` を返した。

## 修正内容

### 修正1: `_parse_obd_response()` の 29bit CAN 対応

ヘッダ判定に 29bit CAN パターン（先頭 `18` + 2桁hex x 4 トークン）を追加。ヘッダ 4 バイト + DL 1 バイト = 5 トークンをスキップしてデータ部を抽出する。

### 修正2: ECU スキャンをブロードキャスト方式に全面変更

個別ヘッダ設定（`ATSH7E0` → `0100`）方式は 29bit CAN で動作しないため、
ブロードキャスト `0100` を1回送信し、応答ヘッダから複数 ECU を識別する方式に変更。

- 11bit CAN: `7E8 06 41 00 ...` → request ID `7E0` として検出
- 29bit CAN: `18 DA F1 0E 06 41 00 XX XX XX XX` → source addr `0E` から ECU 識別

`_scan_can_ecus_broadcast()` メソッドを新規追加し、`scan_ecus()` から呼び出す。
従来の `_probe_can_ecu()` は個別 ECU への通信で引き続き使用可能。

## テスト結果

145 テスト全 PASS（修正後）

## 教訓

- ELM327 クローン品の存在を CON-01 で認識していたが、ECU スキャンの設計時にクローン品の制約（UDS 未対応）を考慮できていなかった
- CAN アドレッシングは 11bit / 29bit の両方を前提とすべきだった。hw-requirement-spec.md に 29bit 対応の要求が欠落していた
- **実機テストの重要性**: シミュレータでは発見できない互換性問題が実機で初めて発覚した

## 横展開

| 箇所 | 29bit CAN 対応 | クローン対応 | 状態 |
|------|---------------|-------------|------|
| PID 検出 (`detect_supported_pids`) | 修正済み | N/A | fixed |
| ECU プローブ (`_probe_can_ecu`) | 修正済み | 修正済み | fixed |
| DTC 読取 (`read_dtcs`) | 要確認 | 要確認 | pending |
| DID スキャン (`scan_dids`) | 要確認 | 要確認 | pending |
| ダッシュボード (`poll_pid`) | 要確認 | N/A | pending |

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "defect 票作成・修正完了"
-->

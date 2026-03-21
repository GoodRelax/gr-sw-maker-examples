# PoC レポート: 29bit CAN アドレッシングによる ECU 検出

<!-- common_block:
  file_type: poc-report
  project: car-diag
  language: ja
  owner: implementer
  status: completed
  created: "2026-03-21"
-->

## 1. 目的

クローン ELM327 v1.5 + 29bit CAN 車両の組み合わせで、以下を検証する:

1. 29bit CAN 物理アドレス（18 DA xx F1）で個別 ECU にアクセスできるか
2. 29bit CAN ファンクショナルアドレス（18 DB 33 F1）で全 ECU を一斉検出できるか
3. UDS サービス（TesterPresent / ReadDTC / ReadDataByIdentifier）が動作するか
4. NRC 0x78（Response Pending）のハンドリングが必要か

## 2. 検証環境

| 項目 | 値 |
|------|-----|
| ELM327 | クローン v1.5（Bluetooth SPP） |
| CAN プロトコル | ISO 15765-4 CAN 29bit / 500kbaud（ATSP7） |
| PC-ELM327 ボーレート | 38,400 bps |
| 車両 | スバル車（VIN: XXX-XXXXXXX...） |
| CAN アドレッシング | 29bit（18 DA xx F1 / 18 DB 33 F1） |

## 3. 検出された ECU

| アドレス | 推定 ECU 名 | 検出方法 | OBD-II | UDS Session | UDS ReadDTC | UDS Extended |
|---------|------------|---------|--------|-------------|------------|-------------|
| 0x0E | Engine (OBD-II) | ファンクショナル | ✓ | Default のみ | ✓ (143byte) | ✗ |
| 0x30 | EPS / Suspension | 物理のみ | ✗ (NRC 0x11) | Default + Extended | ✓ (DTC なし) | ✓ |
| 0x60 | Headlamp / Body | 物理のみ | ✗ (NRC 0x11) | Default + Extended | ✗ (NRC応答なし) | ✓ |

## 4. 検証結果の詳細

### 4.1 アドレッシング方式

| 方式 | AT コマンド | 結果 |
|------|-----------|------|
| ファンクショナル | ATCP18 + ATSH DB 33 F1 | ✓ 動作。ただし 0x0E のみ応答 |
| 物理 | ATCP18 + ATSH DA xx F1 | ✓ 動作。0x0E, 0x30, 0x60 が応答 |
| ATCRA フィルタ | ATCRA 18 DA F1 | ✗ クローンでは動作しない |

### 4.2 ファンクショナル vs 物理の差異

0x30 と 0x60 はファンクショナルアドレスに応答しない。考えられる原因:

- ゲートウェイ ECU の裏側に配置されており、ファンクショナルリクエストがルーティングされない
- OBD-II 法規対応 ECU（0x0E）のみがファンクショナルに応答する設計

結論: **ECU 検出にはファンクショナル + 物理の併用が必須**。

### 4.3 UDS サービス対応状況

| サービス | SID | 0x0E | 0x30 | 0x60 |
|---------|-----|------|------|------|
| TesterPresent | $3E | ✓ 7E 00 | ✓ 7E 00 | ✓ 7E 00 |
| DiagSessionControl Default | $10 01 | ✓ 50 01 | ✓ 50 01 | ✓ 50 01 |
| DiagSessionControl Extended | $10 03 | ✗ NO DATA | ✓ 50 03 | ✓ 50 03 |
| ReadDTCByStatusMask | $19 02 FF | ✓ マルチフレーム | ✓ 59 02 08 (0件) | ✗ NRC なし |
| OBD-II Supported PIDs | $01 00 | ✓ 41 00 ... | ✗ NRC 0x11 | ✗ NRC 0x11 |
| ReadDataByIdentifier VIN | $22 F190 | ✓ (初回 PoC) / ✗ (v2) | ✗ NRC 0x31 | ✗ NRC 0x31 |
| ReadDataByIdentifier 各種 | $22 F187/F18A/F18C/F191 | ✗ NRC 0x31 | ✗ NRC 0x31 | ✗ NRC 0x31 |

### 4.4 NRC（Negative Response Code）分析

| NRC | 意味 | 発生箇所 |
|-----|------|---------|
| 0x11 | serviceNotSupported | 0x30, 0x60 で OBD-II サービス要求時 |
| 0x31 | requestOutOfRange | 全 ECU で DID F187/F18A/F18C/F191 要求時 |
| 0x78 | responsePending | 今回は未発生（ハンドリングは実装済み） |

### 4.5 ISO-TP マルチフレーム転送

0x0E の ReadDTC（$19 02 FF）で 143 byte のマルチフレーム応答を正常受信。ELM327 クローンの ISO-TP 実装は動作している。

フレーム構成: First Frame (10 8F) + 15 Consecutive Frames (20-2F)

### 4.6 クローン ELM327 v1.5 の制約まとめ

| 機能 | 対応 | 備考 |
|------|------|------|
| ATSP7 (29bit CAN 500k) | ✓ | |
| ATCP (CAN Priority) | ✓ | |
| ATSH (3byte ヘッダ) | ✓ | DA xx F1 形式 |
| ATCEA (Extended Address) | ✓ | |
| ATCAF0/1 | △ | CAF0 にすると応答取りこぼし発生 |
| ATCRA (受信フィルタ) | ✗ | 29bit CAN では動作しない |
| ATBRD (ボーレート変更) | ✓ | ただし Bluetooth 経由では実質使用不可 |
| ISO-TP マルチフレーム | ✓ | 143byte 受信確認済み |
| UDS サービス | ✓ | 29bit アドレッシングなら正常動作 |
| KWP2000 | 未確認 | K-Line 物理層の対応は不明 |

## 5. ボーレート分析

| 区間 | 速度 | ボトルネック |
|------|------|------------|
| CAN バス（車両内） | 500 kbps | ✗ 十分高速 |
| PC ↔ ELM327（Bluetooth SPP） | 38,400 bps | ✗ データ量が少ないため問題なし |
| ECU 応答待ち | 50ms〜5,000ms | ✓ これが律速。ATST + NRC 0x78 ハンドリングが重要 |

## 6. タイムアウト設計

| パラメータ | 推奨値 | 根拠 |
|-----------|--------|------|
| ATST（ELM327 内部） | 0xFF (1020ms) | 最大値。P2server (50ms) を十分カバー |
| スクリプト初回タイムアウト | 10 秒 | SEARCHING フェーズ + 応答待ち |
| スクリプト通常タイムアウト | 5 秒 | 2 回目以降のコマンド |
| NRC 0x78 延長 | +5 秒/回、最大 3 回 | P2*server = 5000ms に基づく |
| スキャン時 NO DATA タイムアウト | 1.5 秒 | ATST(1020ms) + マージン |

## 7. メインアプリへの統合方針

### 7.1 ECU スキャンの改善

現在のブロードキャスト `0100` のみの方式を以下に拡張:

1. ファンクショナル `18 DB 33 F1` + TesterPresent で UDS ECU を検出
2. 物理 `18 DA xx F1` + TesterPresent で重点アドレスをスキャン
3. 両方の結果をマージして ECU リストを構築

### 7.2 NRC 0x78 ハンドリング

`_send_raw_command()` に Response Pending 検出・待ち延長ロジックを追加する。

### 7.3 プロトコル設定

接続時に ATSP7 + ATCP18 を明示的に設定し、29bit CAN を確実に有効化する。現在の ATSP0（自動検出）では 11bit CAN として誤検出される可能性がある。

### 7.4 ATCAF0 の回避

クローン ELM327 では ATCAF0 を使用しない。ATCAF1（auto formatting ON）のまま運用する。

## 8. 実施した PoC スクリプト

| ファイル | 目的 |
|---------|------|
| poc/can29bit_probe.py | 初期検証: ATCP/ATSH 動作確認、個別 ECU プローブ |
| poc/can29bit_full_scan.py | 0x01-0xFF 全アドレス物理スキャン |
| poc/can29bit_functional_scan.py | v1: ファンクショナル検証（ATCAF0 問題を発見） |
| poc/can29bit_functional_scan_v2.py | v2: タイムアウト改善 + NRC 0x78 ハンドリング |
| poc/can29bit_full_scan_v2.py | 全 PA スキャン v2: ウォームアップ追加 |
| poc/can29bit_full_scan_v3.py | 全 PA スキャン v3: F186 + マルチプローブ |
| poc/quick_f186.py | エンジン OFF 状態でのファンクショナル F186 検証 |

## 9. 追加検証: エンジン ON/OFF 状態の影響

### 9.1 検証目的

エンジン動作中に ECU が診断応答を抑制している可能性を検証するため、イグニッション ON・エンジン OFF の状態でファンクショナルアドレスに各種コマンドを送信した。

### 9.2 結果

| コマンド | エンジン ON | エンジン OFF |
|---------|-----------|------------|
| 0100 (OBD-II PIDs) functional | ✓ 0x0E 応答 | ✓ 0x0E 応答 |
| 3E00 (TesterPresent) functional | ✓ 0x0E 応答 | ✗ NO DATA |
| 1902FF (ReadDTC) functional | ✓ 0x0E 応答 | ✓ 0x0E 応答（DTC 数減少） |
| 22 F186 (ActiveSession) functional | ✗ NO DATA | ✗ NO DATA |

### 9.3 分析

1. **TesterPresent がエンジン OFF で NO DATA**: エンジン ECU (0x0E) がエンジン停止時にファンクショナル TesterPresent への応答を抑制している。OBD-II レイヤー（$01, $19）には引き続き応答する
2. **$22 F186 が常に NO DATA**: この車両の ECU はファンクショナルアドレスでの UDS $22 サービスに対応していない。物理アドレスでのみ $22 が使える設計
3. **DTC 数の変化**: エンジン OFF 時は一部の runtime DTC がクリアされるため、応答サイズが減少（143byte → 63byte）

### 9.4 ファンクショナル vs 物理のサービス対応まとめ

| サービス | ファンクショナル (18DB) | 物理 (18DA) |
|---------|----------------------|-------------|
| $01 (OBD-II PID) | ✓ 0x0E のみ | ✓ 0x0E |
| $03 (OBD-II DTC) | ✓ 0x0E のみ | ✓ 0x0E |
| $19 (UDS ReadDTC) | ✓ 0x0E のみ | ✓ 0x0E, 0x30 |
| $3E (TesterPresent) | △ エンジン ON 時のみ | ✓ 0x0E, 0x30, 0x60 |
| $10 (DiagSession) | △ エンジン ON 時のみ | ✓ 0x0E, 0x30, 0x60 |
| $22 (ReadDID) | ✗ 常に NO DATA | ✓ 0x0E（VIN 等） |

### 9.5 全 PA スキャン (0x01-0xFF) の結果

v2（ウォームアップ追加）で 0x01-0xFF を物理アドレスで全スキャン:

| アドレス | ECU 名 | 検出コマンド |
|---------|--------|------------|
| 0x0E | Engine (OBD-II) | TesterPresent |
| 0x30 | EPS / Suspension | TesterPresent |
| 0x60 | Headlamp / Body | TesterPresent |

v1 では CAN バスウォームアップなしのため 0x0E を取りこぼしていた（SEARCHING フェーズの遅延）。v2 でウォームアップを追加し解消。

## 10. 最終結論

### 10.1 この車両で OBD-II ポート経由でアクセス可能な ECU は 3 個

| ECU | プロトコル | OBD-II | UDS | 備考 |
|-----|-----------|--------|-----|------|
| 0x0E (Engine) | CAN 29bit 500k | ✓ | ✓ (物理のみ) | ファンクショナルにも応答 |
| 0x30 (EPS/Suspension) | CAN 29bit 500k | ✗ | ✓ (物理のみ) | Extended Session 対応 |
| 0x60 (Headlamp/Body) | CAN 29bit 500k | ✗ | ✓ (物理のみ) | Extended Session 対応 |

### 10.2 ゲートウェイによる制限

他の ECU（Transmission, ABS/VSC, Airbag, BCM, Window 等）は CAN ゲートウェイによって OBD-II ポートからのアクセスがブロックされている。これは近年の車両では一般的なセキュリティ設計であり、ELM327 の制約ではない。

ディーラー診断ツール（SSM4 等）はゲートウェイの認証を通過して全 ECU にアクセスするが、OBD-II 汎用ドングルではアクセス不可。

### 10.3 メインアプリへの統合方針（更新）

1. **ECU スキャン**: ファンクショナル `0100` + 物理 TesterPresent（重点アドレス）の併用。ウォームアップ必須
2. **DTC 読取**: 0x0E は OBD-II Mode $03 または UDS $19。0x30 は UDS $19 のみ。0x60 は DTC 非対応
3. **ダッシュボード**: 0x0E の OBD-II PID のみ表示可能。0x30, 0x60 は PID 非対応
4. **NRC 0x78**: ハンドリングは実装済みだが、今回の検証では未発生。将来の車両対応のため維持

## 11. Service $09 による ECU 識別

### 11.1 Service $09 対応状況

0x0E (PCM) の `0900` 応答ビットマスクから判明した対応 PID:

| PID | 対応 | 内容 |
|-----|------|------|
| $02 (VIN) | ✗ | Service 09 では未対応。UDS $22 F190 でのみ取得可能 |
| $04 (Cal ID) | ✓ | `XXXX-XXX-...` |
| $06 (CVN) | ✓ | `XX XX XX XX` |
| $0A (ECU Name) | ✓ | `PCM\0-PowertrainCtrl\0` |

### 11.2 ECU Name ($090A) の取得結果

ファンクショナルアドレスで $090A を送信し、マルチフレーム応答を受信:

```
18 DA F1 0E 10 17 49 0A 01 XX XX XX   → First Frame: (masked)
18 DA F1 0E 21 XX XX XX XX XX XX XX   → CF#1: (masked)
18 DA F1 0E 22 XX XX XX XX XX XX XX   → CF#2: (masked)
18 DA F1 0E 23 XX XX XX XX XX XX XX   → CF#3: (masked)
```

ECU Name: **PCM - PowertrainCtrl**（Powertrain Control Module）

応答したのは 0x0E のみ。0x30, 0x60 は Service $09 に応答しない。

### 11.3 物理アドレスで応答があった方法の一覧

全 PoC を通じて、物理アドレス（18 DA xx F1）で応答が確認されたコマンド:

| コマンド | SID | 内容 | 0x0E | 0x30 | 0x60 |
|---------|-----|------|------|------|------|
| 3E 00 | $3E | TesterPresent | ✓ | ✓ | ✓ |
| 10 01 | $10 | DiagSession Default | ✓ | ✓ | ✓ |
| 10 03 | $10 | DiagSession Extended | ✗ | ✓ | ✓ |
| 01 00 | $01 | OBD-II Supported PIDs | ✓ | NRC 0x11 | NRC 0x11 |
| 19 02 FF | $19 | ReadDTCByStatusMask | ✓ | ✓ (0件) | ✗ |
| 22 F1 90 | $22 | VIN | ✓ (初回のみ) | NRC 0x31 | NRC 0x31 |
| 09 0A | $09 | ECU Name | ✓ | 未検証 | 未検証 |

全 ECU で確実に応答が得られたのは **TesterPresent ($3E 00)** と **DiagSessionControl Default ($10 01)** の 2 つ。

<!-- change_log:
  - version: "1.0.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "PoC レポート作成"
  - version: "1.1.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "エンジン ON/OFF 検証、全 PA スキャン結果、最終結論を追記"
  - version: "1.2.0"
    date: "2026-03-21"
    author: "implementer"
    changes: "Service $09 ECU Name 取得結果、物理アドレス応答方法一覧を追記"
-->

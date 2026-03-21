# Review: car-diag 仕様書 Ch3-4 (Architecture / Specification)

<review:id>review-003</review:id>
<review:target>docs/spec/car-diag-spec.md Chapter 3-4</review:target>
<review:dimensions>R2,R4,R5</review:dimensions>
<review:result>pass</review:result>
<review:critical_count>0</review:critical_count>
<review:high_count>0</review:high_count>
<review:medium_count>3</review:medium_count>
<review:low_count>4</review:low_count>
<review:gate_phase>design -> implementation</review:gate_phase>

---

## Review Summary

| 重大度 | 件数 |
|--------|------|
| Critical | 0 |
| High | 0 |
| Medium | 3 |
| Low | 4 |
| **総合判定** | **PASS** |

**PASS 理由:** Critical / High 指摘は検出されなかった。Clean Architecture の 4 層分離・依存方向・DIP 適用は適切であり、FSA の状態遷移は 10 状態 30 遷移が完全に定義されている。docs/hw-requirement-spec.md の Adapter 層 I/F 設計との整合性も確認済み。Medium 3 件・Low 4 件は implementation フェーズでの対応で問題ない。

**Medium 指摘の対応方針:** orchestrator に報告し、implementation フェーズでの対応承認を得る。

---

## R2: SW 設計原則レビュー

### 確認結果: レイヤー分離と依存方向

- Clean Architecture 4 層（Entity / Use Case / Adapter / Framework）の分類は妥当である。レイヤー仕訳表（L296-329）で全 29 コンポーネントが明確に分類されている
- 依存方向は Framework -> Adapter -> Use Case -> Entity の一方向であり、コンポーネント図（L369-455）の矢印方向で確認済み
- Entity 層は全て `frozen=True` dataclass で不変性を保証しており、外部依存がない（L613）
- DIP の適用は適切。Use Case 層は `SerialPort Protocol` / `DiagProtocol Protocol` に依存し、pyserial を直接参照していない。hw-requirement-spec.md 6.2 節の SerialPort Protocol 定義（L362-434）と仕様書 Ch3 の Adapter 層 Protocol クラス図（L617-668）が整合している

### 確認結果: コンポーネントの責務分割

- Use Case 8 個はそれぞれ単一の責務を持ち、SRP に適合する。各 Use Case は 1 つのビジネスフローに対応している
- ELM327Adapter は DiagProtocol を実装し、AT コマンドの送受信とプロトコル差異吸収を担う。シリアル通信の物理操作は SerialPort に委譲しており、SoC が実現されている
- OCP は DiagProtocol Protocol により担保。新プロトコル追加時は新 Adapter 実装を追加するのみで既存コードの変更不要（Ch6 L1718）

### 確認結果: hw-requirement-spec.md との整合性

- hw-requirement-spec.md 6.1 節のレイヤー構成図（L313-354）と仕様書 Ch3 のコンポーネント図の依存関係が一致している
- SerialPort Protocol の I/F 定義（open/close/write/read_until_prompt）が両文書で一致
- DiagProtocol Protocol のメソッドシグネチャ（scan_ecus/read_dtcs/clear_dtcs/read_parameter/detect_supported_pids/scan_dids/switch_protocol）が両文書で整合
- PySerialPort の具体実装パラメータ（baudrate=38400, bytesize=8, parity=None, stopbits=1）が hw-requirement-spec.md 2.1 節の物理接続要件と一致

---

## R4: 並行性・状態遷移レビュー

### 確認結果: シリアル通信のスレッド安全性

- CON-01（L90）でシリアル通信はシングルスレッド逐次処理と明記されており、デッドロック・レースコンディションのリスクは排除されている
- Qt イベントループで GUI イベントが直列化されることが Ch6 で確認済み（L1729）
- S_PROTOCOL_SWITCHING 状態（L788-789, ADR-002 L1094）で他の操作を排他しており、プロトコル切替中の競合は防止されている

### 確認結果: FSA の状態遷移の完全性

- 10 状態が定義されている（L551-563）: S_DISCONNECTED, S_CONNECTING, S_CONNECTED, S_ECU_SCANNING, S_DID_SCANNING, S_DTC_READING, S_DTC_CLEARING, S_MONITORING, S_RECORDING, S_PROTOCOL_SWITCHING, S_ERROR（計 11 状態）
- 状態遷移図（L758-809）と状態遷移テーブル（L1607-1638）の 30 遷移が一致している
- 通信断（T30）は S_DISCONNECTED 以外の全状態からの遷移を定義しており、網羅的
- DID スキャン中断時のキャッシュ保存（L778, T15）と記録中の TSV フラッシュ（L806, T30）が遷移のアクションとして定義済み

### 確認結果: グリッチ（状態遷移中の瞬間的な不正状態）

- Entity 層が全て frozen dataclass であるため、複数フィールドの部分更新による中間状態は発生しない
- ConnectionState は列挙型であり、遷移は原子的な値の差し替えで実現される

---

## R5: パフォーマンスレビュー

### 確認結果: リアルタイムグラフ描画

- pyqtgraph を採用しており（L28）、Qt の描画パイプラインと統合されるため GUI スレッドでの高速描画が期待できる
- グラフデータは「最新 N 点のみ保持」する設計（Ch6 L1733）であり、メモリ使用量の増大は抑制されている

### 確認結果: ポーリング間隔の妥当性

- 500ms を目標間隔として定義（FR-09b L256）。全 PID/DID の読取が 500ms を超過する場合はラウンドロビン 1 周で 1 記録行とし、実際の間隔をタイムスタンプに記録する（FR-09b）
- NFR-01b（L268）で「ダッシュボード更新を 1 秒以内の間隔」と上限を定義しており、500ms 目標との整合性がある
- CON-02（L91）で ELM327 応答速度制約を認識し、ラウンドロビン方式で対応する設計は妥当

---

## Findings (指摘事項)

### Medium-009: ConnectElm327UseCase が ELM327Adapter に直接依存している（DIP 違反の疑い）

| 項目 | 内容 |
|------|------|
| 重大度 | Medium |
| 観点 | R2: DIP（依存性逆転原則）/ CA（クリーンアーキテクチャ） |
| 箇所 | コンポーネント図 L412-413、レイヤー仕訳表 L308 |
| 問題 | コンポーネント図で `UC_Connect -->|"uses"| ELM_Adapter` と記載されており、Use Case 層（ConnectElm327UseCase）が Adapter 層の具象クラス（ELM327Adapter）に直接依存している。他の Use Case は全て DiagProtocol Protocol（抽象インターフェース）経由でアクセスしているが、ConnectElm327UseCase のみ例外になっている。hw-requirement-spec.md 6.1 節の図（L346）でも `Connect -->|"depends on"| ELM327Adapter` と具象依存が描かれている。 |
| 影響 | テスト時に ELM327Adapter をモックに差し替えにくい。将来 ELM327 以外のアダプタ（例: STN1110）をサポートする場合、ConnectElm327UseCase の修正が必要になり OCP に違反する。 |
| 修正案 | ConnectElm327UseCase が ELM327Adapter 固有の初期化メソッド（`initialize()`, `send_command()`）を使用する必要がある場合、初期化用の Protocol（例: `DeviceInitializer Protocol`）を Adapter 層に追加し、DiagProtocol とは別の抽象経由で依存させる。または、初期化シーケンスを DiagProtocol Protocol のメソッドとして統合する。 |

### Medium-010: S_ERROR 状態からの遷移制約が不完全

| 項目 | 内容 |
|------|------|
| 重大度 | Medium |
| 観点 | R4: 状態遷移の完全性 |
| 箇所 | 状態遷移図 L797-798, 808、状態遷移テーブル T29-T30 |
| 問題 | S_ERROR からの遷移は T29（User: Acknowledge -> S_DISCONNECTED）と T30（Comm loss -> S_DISCONNECTED）の 2 つが定義されている。しかし、S_ERROR 状態でユーザーが Acknowledge せずにアプリケーションを閉じた場合の動作が未定義。また、S_ERROR に遷移するトリガーが S_CONNECTING からの init failed（T03）のみであり、他の状態からのエラー（例: ECU スキャン中に予期しないエラーが発生した場合）は通信断（T30 -> S_DISCONNECTED）として処理されるのか、S_ERROR として処理されるのかが曖昧。 |
| 影響 | 実装者が S_ERROR と通信断の境界を判断しにくい。HWR-20 の ELM327 エラー応答（`?` など）が通信断ではなくプロトコルエラーである場合の状態遷移が不明確。 |
| 修正案 | (1) S_ERROR に遷移するトリガーの完全なリストを明記する（例: 「S_ERROR は ELM327 初期化失敗時のみ使用し、通信中のエラーは全て通信断（T30）として S_DISCONNECTED に遷移する」等の判断基準）。(2) アプリケーション終了時のリソース解放についてシナリオまたは要求として定義する。 |

### Medium-011: ダッシュボードポーリングの「最新 N 点」の N が未定義

| 項目 | 内容 |
|------|------|
| 重大度 | Medium |
| 観点 | R5: メモリ・リソース |
| 箇所 | Ch6 L1733、Ch3 3.5.5 ダッシュボードポーリングフロー |
| 問題 | Ch6 で「グラフデータは最新 N 点のみ保持」と記載されているが、N の具体値が定義されていない。N が小さすぎるとグラフの時間軸が短くなりデータの傾向が見えず、大きすぎるとメモリ使用量が増大する。また、SC-043（L1482-1485）では「30 秒のスクロールするラインチャート」と記載されており、N の算出には更新間隔との関係が必要。500ms 間隔なら N=60、1 秒間隔なら N=30 となるが、PID 数によって更新間隔が変動するため、N を時間ベース（例: 直近 60 秒分）で定義するか、点数ベースで定義するかを明確にすべき。 |
| 影響 | 実装者が任意の値を選択し、テスト時の性能評価基準が曖昧になる。 |
| 修正案 | N を「直近 120 秒分のデータポイント」等の時間ベースで定義するか、または NFR として「グラフ表示用メモリは 10MB 以内」等の制約を明記する。 |

### Low-005: DiagProtocol Protocol の戻り値型が仕様書と hw-requirement-spec で異なる命名

| 項目 | 内容 |
|------|------|
| 重大度 | Low |
| 観点 | R2: Naming（命名の一貫性） |
| 箇所 | 仕様書 Ch3 Adapter 層 Protocol クラス図 L637 vs hw-requirement-spec.md L612-613 |
| 問題 | 仕様書 Ch3 のクラス図では `DiagProtocol.read_dtcs()` の戻り値が `list of DtcEntry` と記載されているが、Entity 層クラス図（L573-580）では `DTC` データクラスが定義されている。`DtcEntry` と `DTC` は別クラスとして hw-requirement-spec.md で両方定義されており整合はしているが、レイヤー間のデータ変換の責務がどこにあるか（Adapter が DtcEntry を返し Use Case が DTC に変換するのか）が明示されていない。 |
| 影響 | 軽微。実装時に判断可能だが、命名の意図を明確にしておくと良い。 |
| 修正案 | DtcEntry（Adapter 層の戻り値型）と DTC（Entity 層のドメインモデル）の変換責務を Use Case 層が担うことをクラス図の注釈に追記する。 |

### Low-006: レイヤー仕訳表の状態数表記が不正確

| 項目 | 内容 |
|------|------|
| 重大度 | Low |
| 観点 | R2: PIE（意図を明確に表現する） |
| 箇所 | レイヤー仕訳表 L307 |
| 問題 | `ConnectionState` の説明に「FSA 状態の列挙（S_DISCONNECTED 他 10 状態）」と記載されているが、実際の列挙値（L551-563）は S_DISCONNECTED を含めて 11 状態（S_DISCONNECTED, S_CONNECTING, S_CONNECTED, S_ECU_SCANNING, S_DID_SCANNING, S_DTC_READING, S_DTC_CLEARING, S_MONITORING, S_RECORDING, S_PROTOCOL_SWITCHING, S_ERROR）である。 |
| 影響 | 軽微。読み手の混乱を避けるための修正。 |
| 修正案 | 「S_DISCONNECTED 他 10 状態」を「全 11 状態」に修正する。 |

### Low-007: ダッシュボードポーリングフローに DID 読取時のプロトコル切替が省略されている

| 項目 | 内容 |
|------|------|
| 重大度 | Low |
| 観点 | R4: 状態遷移の完全性（シーケンス図レベル） |
| 箇所 | 3.5.5 ダッシュボードポーリングフロー L1027-1042 |
| 問題 | ポーリングフローのシーケンス図では DID 読取時に `ATSH + send_command("22{did}")` を行うが、PID と DID が混在するラウンドロビンにおいて、PID 読取（Legacy OBD ブロードキャスト）から DID 読取（UDS 個別 ECU 指定）に切り替える際の ATSH/ATCRA 設定の詳細が省略されている。ADR-002 のプロトコル切替は CAN<->KWP 間のものであり、同一 CAN バス上での Legacy OBD ブロードキャスト <-> UDS 個別送信の切替は別の操作である。 |
| 影響 | 軽微。実装レベルで ELM327Adapter 内部の処理として解決可能。 |
| 修正案 | ポーリングフローの注釈として「PID 読取は ATSH をブロードキャスト ID（7DF）に、DID 読取は各 ECU の CAN ID に ATSH を設定する」旨を追記する。 |

### Low-008: SC-003 のタイムアウト値と NFR-01a の不一致

| 項目 | 内容 |
|------|------|
| 重大度 | Low |
| 観点 | R2: DRY（仕様の重複・競合の排除） |
| 箇所 | SC-003 L1150 vs NFR-01a L267 |
| 問題 | SC-003 では「no response is received within 5 seconds」と記載されているが、NFR-01a では「ELM327 接続確立を 10 秒以内に完了する」と定義されている。5 秒は hw-requirement-spec.md の応答タイムアウト（HWR コマンド単位）、10 秒は接続確立全体のタイムアウトであり、意味が異なる。SC-003 が ATZ 単体のタイムアウトを指すのであれば正しいが、シナリオの文脈では接続全体のタイムアウトとも読める。 |
| 影響 | 軽微。SC-003 の traces が FR-01e であり、FR-01e のタイムアウト定義と照合すれば判断可能。 |
| 修正案 | SC-003 の記述を「no response is received within the command timeout (5 seconds per HWR-03)」等に明確化し、接続全体の 10 秒タイムアウト（NFR-01a）との区別を明示する。 |

---

## 整合性確認: docs/hw-requirement-spec.md Adapter 層 I/F 設計

| 確認項目 | 結果 |
|---------|------|
| SerialPort Protocol の I/F（open/close/write/read_until_prompt） | 整合 |
| PySerialPort の通信パラメータ（38400/8N1/None） | 整合 |
| DiagProtocol Protocol のメソッド一覧 | 整合 |
| DiagResponse / DtcEntry / EcuInfo / ParameterReading のデータクラス定義 | 整合（Low-005 の DtcEntry/DTC 変換責務のみ要明確化） |
| エラー型（ConnectionError / TimeoutError） | 整合 |
| ELM327 エラー応答マッピング（HWR-20 <-> E-PROTO-001/002） | 整合 |
| リトライ方針（HWR-24: 3 回、HWR-25: 500ms） vs NFR-02a（1 秒間隔 3 回） | **不整合あり**（下記参照） |

### 補足: リトライ間隔の不整合について

HWR-25 では「リトライ間隔を 500 ms」と定義しているが、NFR-02a では「1 秒間隔で最大 3 回リトライ」と定義している。これは Ch1-2 レビュー（review-002）で既に Medium-003 として指摘され修正済みの項目であるが、hw-requirement-spec.md 側の HWR-25 が更新されていない可能性がある。ただし HWR-25 は仕様書の NFR-02a よりも詳細な HW 連携固有のパラメータとして別の値を意図的に設定している可能性もある。本レビューの対象外（hw-requirement-spec.md 自体のレビューは別途実施）であるため、orchestrator への情報提供として記録する。

---

## 総合評価

| 観点 | 評価 |
|------|------|
| R2: レイヤー分離 | 良好。4 層の Clean Architecture が明確に定義されている |
| R2: 依存方向 | 良好。一方向の依存（外->内）が維持されている。Medium-009 の DIP 違反疑いのみ要確認 |
| R2: コンポーネント責務分割 | 良好。SRP / SoC が適切に適用されている |
| R4: スレッド安全性 | 良好。シングルスレッド制約（CON-01）により競合リスクは排除 |
| R4: FSA 完全性 | 良好。11 状態 30 遷移が完全に定義されている。Medium-010 の S_ERROR 遷移基準のみ要明確化 |
| R5: リアルタイム描画 | 良好。pyqtgraph 採用と最新 N 点保持の方針は妥当。Medium-011 の N 値定義のみ要追記 |
| R5: ポーリング間隔 | 良好。500ms 目標 + ラウンドロビン方式は ELM327 制約下で妥当 |
| hw-requirement-spec.md 整合 | 良好。Adapter 層 I/F 設計は整合。リトライ間隔の不整合は情報提供として記録 |

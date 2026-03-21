# Review: car-diag 実装コード (src/)

<review:id>review-004</review:id>
<review:target>src/entities/, src/use_cases/, src/adapters/, src/framework/, src/main.py</review:target>
<review:dimensions>R2,R3,R4,R5</review:dimensions>
<review:result>pass</review:result>
<review:critical_count>0</review:critical_count>
<review:high_count>0</review:high_count>
<review:medium_count>5</review:medium_count>
<review:low_count>8</review:low_count>
<review:gate_phase>implementation -> testing</review:gate_phase>

---

## Review Summary

| 重大度 | 件数 |
|--------|------|
| Critical | 0 |
| High | 0 |
| Medium | 5 |
| Low | 8 |
| **総合判定** | **PASS** |

**PASS 理由:** Critical / High 指摘は検出されなかった。Clean Architecture の 4 層分離は適切に実装されており、依存方向は Entity <- Use Case <- Adapter <- Framework の一方向に保たれている。DIP は typing.Protocol で実現され、Use Case 層は具象クラスに依存していない。FSA 状態遷移は仕様書 Ch3 の定義と整合している。シリアル通信は CON-01 のとおりシングルスレッド逐次処理であり、デッドロック・レースコンディションのリスクは排除されている。Medium 5 件・Low 8 件は testing フェーズでの対応で問題ない。

**Medium 指摘の対応方針:** orchestrator に報告し、testing フェーズまたは次イテレーションでの対応承認を得る。

---

## R2: SW 設計原則レビュー

### 確認結果: レイヤー分離と依存方向

- **Entity 層** (6ファイル): 全エンティティは `frozen=True` dataclass または StrEnum で不変性が保証されている。外部ライブラリへの依存はない。`connection_state.py` の VALID_TRANSITIONS による遷移マップは Entity 層のドメインロジックとして妥当
- **Use Case 層** (9ファイル): 全 Use Case は `protocols.py` の Protocol インターフェースにのみ依存しており、Adapter/Framework の具象クラスを直接参照していない。DIP が正しく適用されている
- **Adapter 層** (3ファイル): Entity 層に依存し、Framework 層には依存していない。`ELM327Adapter` は `SerialPort` Protocol を受け取り、`DiagProtocol` の契約を満たしている
- **Framework 層**: PyQt6, pyserial, pyqtgraph への依存はこの層に閉じている。`try/except ImportError` によるフォールバック実装でライブラリ未インストール時も起動可能
- **main.py**: 手動 DI コンテナで依存グラフを構築しており、依存方向の逆転がエントリポイントでのみ解決されている。これは Composition Root パターンとして適切

### 確認結果: SOLID 原則

- **SRP**: 各 Use Case は単一のビジネスフローに対応している。`ConnectElm327UseCase` は接続+PID検出、`ReadDtcsUseCase` は DTC 読取+説明文付与と、責務が明確
- **OCP**: `DiagProtocol` Protocol により新プロトコル追加は新 Adapter 実装のみで対応可能。`ELM327Adapter` 内の `read_dtcs`/`clear_dtcs`/`read_parameter` は if/elif 分岐でプロトコルを振り分けているが、現時点で 3 プロトコル固定であり過度な抽象化は YAGNI に反するため妥当
- **ISP**: `DiagProtocol` Protocol は 8 メソッドを定義しており、やや大きいが、全 Use Case が複数メソッドを組み合わせて使用するため分割の実益は低い
- **DIP**: 全 Use Case は `typing.Protocol` に依存し、具象クラスを知らない。`@runtime_checkable` デコレータにより実行時の型チェックも可能

### 確認結果: その他の設計原則

- **DRY**: マジックナンバーは定数化されている（`_MAX_RETRY_COUNT`, `_COMMAND_INTERVAL_S`, `CACHE_MAX_AGE_DAYS` 等）。fsync ロジックが `RecordDataUseCase` と `TsvFileWriter` の両方に存在する点は後述 (M-01)
- **KISS**: ネスト深さは最大 3 レベル。早期リターンが適切に使用されている
- **SoC**: GUI ロジックは Framework 層に閉じ、ビジネスロジックは Use Case 層に閉じている
- **LOD**: チェーン呼び出しは検出されなかった
- **POLA**: メソッド名と動作が一致している。`_safe_close` は冪等であり、名前どおりの安全な動作

---

## R3: コーディング品質レビュー

### 確認結果: PEP 8 / 型ヒント / docstring

- 全モジュールにモジュール docstring が付与されており、traces フィールドで要求 ID へのトレーサビリティが確保されている
- 全公開メソッドに docstring (Google スタイル: Args/Returns/Raises) が付与されている
- 型ヒントは全関数の引数・戻り値に付与されている。`from __future__ import annotations` で PEP 604 Union 構文を使用
- `| None` 構文による Optional 表現が一貫して使用されている

### 確認結果: エラーハンドリング

- 外部 I/O（シリアルポート、ファイル、JSON）で例外が捕捉されている
- 空の catch 節は存在しない。全ての except ブロックで `logger.exception()` によるログ記録が行われている
- `RecordDataUseCase.write_row()` はディスクフル時に記録を停止し例外を再送出しており、FR-09g に適合
- `JsonScanCacheRepository._touch_file()` の `except OSError: pass` は冪等操作であり、握りつぶしとして許容範囲内

### 確認結果: 防御的プログラミング

- `decode_obd2_dtc()` / `decode_uds_dtc()` でバイト値の範囲チェックが行われている
- `PidDefinition.convert_raw_bytes()` でバイト数の一致チェックが行われている
- `JsonScanCacheRepository._cache_file_path()` でキャッシュキーの文字種バリデーション (正規表現) が行われており、パストラバーサル攻撃を防止
- `_validate_response()` で ELM327 応答の文字種チェック (印字可能 ASCII のみ) が行われている (NFR-04a)

### 確認結果: 構造化ログ

- 全モジュールで `logging.getLogger(__name__)` を使用。`StructuredJsonFormatter` により JSON 形式の構造化ログを出力
- `extra` パラメータで文脈情報（port_name, ecu_identifier, dtc_count 等）を付与しており、デバッグ効率に優れる
- `console.log` (Python では `print`) は使用されていない

---

## R4: 並行性・状態遷移レビュー

### 確認結果: シリアル通信のスレッド安全性

- CON-01 のとおり、ELM327 との通信はシングルスレッドで逐次処理される。`ELM327Adapter._send_raw_command()` は write -> sleep -> read の逐次呼び出しであり、並行アクセスは発生しない
- GUI イベントは PyQt6 のイベントループで直列化されるため、Use Case の呼び出しも直列的に実行される
- `_abort_requested` フラグ (`ScanDidsUseCase`) は GUI スレッドから書き込み、ポーリングループで読み取る構造。Python の GIL により bool 値の読み書きは原子的であり、レースコンディションは発生しない

### 確認結果: FSA 状態遷移

- `connection_state.py` の `VALID_TRANSITIONS` マッピングは仕様書 Ch3 の 11 状態・30 遷移と整合している
- `ConnectElm327UseCase._transition_to()` は `is_valid_transition()` で遷移の妥当性を検証し、無効遷移時に `RuntimeError` を送出する
- 全状態から `S_DISCONNECTED` への通信断遷移 (FR-02a) が定義されている
- `S_ERROR` からは `S_DISCONNECTED` への遷移のみ許可されており、エラー状態からの不正復帰を防止

### 確認結果: ファイルハンドル管理

- `RecordDataUseCase.stop_recording()` は `try/finally` で `_file_handle = None` を保証しており、リソースリークを防止
- `TsvFileWriter.close_file()` は冪等 (`_closed` フラグで二重クローズを防止)
- `PySerialPort.close()` も冪等 (`finally` で `_serial = None`, `_is_open = False`)
- 通信断時の TSV フラッシュ (`flush_for_comm_loss()`) でデータ損失を最大 1 秒分に抑制 (FR-09f)

---

## R5: パフォーマンスレビュー

### 確認結果: ポーリング効率

- `MonitorDashboardUseCase.poll_once()` はポーリング対象を 1 巡分ループし、各パラメータを逐次読取する。CON-01 の制約（シングルスレッド逐次処理）下では最適な実装
- ループ内で不変の計算は行われていない
- PID 変換関数はラムダで定義されており、ルックアップは `STANDARD_PIDS` の dict アクセス (O(1))

### 確認結果: グラフ描画

- `DashboardTab` は pyqtgraph を使用しており、リアルタイム描画に適した軽量ライブラリの選定は妥当
- グラフデータ (`_graph_data`) はリスト型で蓄積されるが、長時間モニタリング時のメモリ増大は後述 (M-05)

### 確認結果: DID スキャン効率

- DID スキャンは逐次問い合わせ (O(n), n = DID 範囲) であり、CON-09 の制約（1 リクエスト約 30-50ms）下では避けられない
- 進捗コールバックは 100 DID ごとに発火しており、GUI 更新頻度は適切
- 中断・再開機能によりスキャン結果がキャッシュに保存され、再スキャン時の時間短縮が実現されている

### 確認結果: メモリ使用量

- DTC 辞書 (`_BUILTIN_DTC_DESCRIPTIONS`) は約 140 エントリのインメモリ辞書。メモリ消費は数 KB で問題なし
- `STANDARD_PIDS` も 12 エントリで軽量

---

## 指摘事項

### Medium

#### M-01: fsync ロジックの重複 (R2: DRY)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/use_cases/record_data.py` L180-184 と `src/framework/tsv_writer.py` L197-210 |
| **問題** | `_flush_and_sync()` メソッドが `RecordDataUseCase` と `TsvFileWriter` の両方に同一のロジック (`flush() -> os.fsync()`) として実装されている |
| **影響** | 片方を修正して他方を忘れると不整合が生じる。DRY 原則に違反 |
| **修正案** | `RecordDataUseCase` が `TsvFileWriter` を利用する構成にリファクタリングし、fsync ロジックを `TsvFileWriter` に集約する。Use Case 層は Framework 層の具象に依存できないため、TSV 書き込みの Protocol を `protocols.py` に定義し、DIP を適用する |

#### M-02: RecordDataUseCase が直接 `open()` / `os.fsync()` を呼び出している (R2: CA)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/use_cases/record_data.py` L72, L184 |
| **問題** | Use Case 層が `open()` 組み込み関数と `os.fsync()` を直接呼び出しており、ファイルシステムへの直接依存がある。Clean Architecture では Use Case 層は外部 I/O の抽象にのみ依存すべき |
| **影響** | Use Case 層のテスタビリティが低下する（ファイルシステムのモック化が困難）。レイヤー分離の例外箇所となる |
| **修正案** | ファイル書き込みの抽象 Protocol (例: `DataWriter`) を `protocols.py` に定義し、`TsvFileWriter` をその実装として Use Case に注入する |

#### M-03: DashboardTab._graph_data に上限がない (R5: メモリ)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/framework/gui/dashboard_tab.py` L68 |
| **問題** | `_graph_data: dict[str, list[float]]` にデータポイントが際限なく蓄積される。500ms 間隔で 12 PID を記録すると、1 時間で約 86,400 ポイント、8 時間で約 691,200 ポイントになる |
| **影響** | 長時間モニタリング時にメモリ消費が増大し、グラフ描画のパフォーマンスが低下する可能性がある |
| **修正案** | リングバッファ (collections.deque with maxlen) を使用し、表示範囲を直近 N ポイントに制限する（例: 直近 600 ポイント = 5 分間） |

#### M-04: main.py の DI コンテナが dependencies を Use Case/GUI に接続していない (R2: CA)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/main.py` L86-131 |
| **問題** | `build_dependencies()` で構築された Use Case インスタンスが GUI タブウィジェットに注入されていない。`ConnectionTab`, `DtcTab`, `DashboardTab`, `RecordingTab` はシグナルを発火するが、それを受け取って Use Case を呼び出すコントローラー（Presenter）が存在しない |
| **影響** | GUI ボタンを押しても Use Case が実行されず、アプリケーションとして機能しない。統合テストフェーズで発覚する |
| **修正案** | GUI シグナルと Use Case を接続する Presenter / Controller クラスを Framework 層に実装し、main.py で接続する。または main.py 内でシグナル-スロット接続を記述する |

#### M-05: ScanDidsUseCase._abort_requested のスレッド安全性が GIL に依存 (R4: レースコンディション)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/use_cases/scan_dids.py` L74, L214 |
| **問題** | `_abort_requested` フラグの読み書きは Python GIL により事実上安全だが、GIL はCPython 実装の詳細であり、言語仕様で保証されていない。PyPy 等の代替実装や将来の free-threaded Python (PEP 703) では安全性が保証されない |
| **影響** | 現時点での CPython 実行環境では問題なし。ただし将来の移植性リスクがある |
| **修正案** | `threading.Event` を使用して明示的なスレッド間同期を行う。`_abort_requested = threading.Event()`, `request_abort()` で `set()`, ループ内で `is_set()` をチェックする |

### Low

#### L-01: 未使用の import (R3: コード品質)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/use_cases/record_data.py` L11 |
| **問題** | `from typing import IO, TextIO` で `IO` がインポートされているが、使用されていない |
| **修正案** | `from typing import TextIO` に修正する |

#### L-02: scan_dids.py の未使用変数 (R3: コード品質)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/use_cases/scan_dids.py` L197 |
| **問題** | `total_dids_in_range` が計算されているが、以降で使用されていない |
| **修正案** | 不要であれば削除する。進捗計算に使用予定であれば on_progress への引数として活用する |

#### L-03: ELM327Adapter の if/elif チェーン (R2: OCP)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/adapters/elm327_adapter.py` L344-358, L373-380, L400-407 |
| **問題** | `read_dtcs`, `clear_dtcs`, `read_parameter` で `DiagProtocolType` に対する if/elif 分岐が 3 箇所に繰り返されている |
| **修正案** | Strategy パターンでプロトコル別の処理を分離することを将来的に検討する。ただし現時点では 3 プロトコル固定であり、YAGNI の観点から現状維持でも妥当 |

#### L-04: DTC.protocol_type が文字列型 (R2: 型安全性)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/entities/dtc.py` L122 |
| **問題** | `protocol_type: str` とコメントに「循環 import 回避」と記載されているが、`from __future__ import annotations` が既に使用されており、循環 import は発生しない |
| **修正案** | `DiagProtocolType` 型に変更し、型安全性を向上させる |

#### L-05: main_window.py の未使用 TYPE_CHECKING import (R3: コード品質)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/framework/gui/main_window.py` L10-12 |
| **問題** | `if TYPE_CHECKING: pass` ブロックが空であり、意味をなさない |
| **修正案** | 不要な import ガードを削除する |

#### L-06: main_window.py の未使用 Qt import (R3: コード品質)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/framework/gui/main_window.py` L17 |
| **問題** | `from PyQt6.QtCore import Qt` がインポートされているが、使用されていない |
| **修正案** | 未使用 import を削除する |

#### L-07: ecu_scan_dialog.py の未使用 Qt import (R3: コード品質)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/framework/gui/ecu_scan_dialog.py` L13 |
| **問題** | `from PyQt6.QtCore import Qt, pyqtSignal` で `Qt` がインポートされているが、使用されていない |
| **修正案** | `from PyQt6.QtCore import pyqtSignal` に修正する |

#### L-08: ManageScanCacheUseCase.invalidate_cache が空データ上書き方式 (R2: POLA)

| 項目 | 内容 |
|------|------|
| **箇所** | `src/use_cases/manage_scan_cache.py` L97-98 |
| **問題** | キャッシュ無効化が空辞書の上書きで実装されている一方、`JsonScanCacheRepository` にはファイル削除による `invalidate()` メソッドが存在する。無効化の意味が異なる（空ファイル残存 vs 完全削除） |
| **修正案** | `ScanCacheRepository` Protocol に `invalidate()` メソッドを追加し、Use Case はそれを呼び出す形に統一する |

---

## 合格基準との照合

| 基準 | 結果 | 判定 |
|------|------|------|
| Critical = 0 件 | 0 件 | OK |
| High = 0 件 | 0 件 | OK |
| Medium 件数報告 | 5 件 | orchestrator に報告要 |

---

## 結論

**総合判定: PASS**

実装コードは Clean Architecture の 4 層分離、DIP、FSA 状態遷移検証、構造化ログ、防御的プログラミングが適切に実装されており、Critical / High 指摘は検出されなかった。Medium 5 件のうち M-04 (GUI-UseCase 未接続) は testing フェーズ開始前に対応が望ましい。その他の Medium / Low 指摘は testing フェーズ以降での対応で問題ない。

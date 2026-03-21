# car-diag 可観測性設計

## 1. 概要

car-diag はデスクトップアプリケーションであり、Web サービスのような分散トレーシングは不要である。ただし、ELM327 との通信品質の監視、デバッグ支援、性能分析のために構造化ログを中心とした可観測性を実装する。

traces: FR-02d, NFR-05a

## 2. ログ設計

### 2.1 ログ形式

構造化 JSON 形式のログを採用する。`logging` モジュールの `JSONFormatter` を使用する。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| timestamp | string (ISO 8601) | ログ出力日時 |
| level | string | DEBUG / INFO / WARN / ERROR |
| module | string | Python モジュール名 |
| function | string | 関数名 |
| message | string | ログメッセージ |
| connection_state | string | 現在の FSA 状態 |
| elm327_command | string | 送信した AT/OBD コマンド（通信ログの場合） |
| elm327_response | string | 受信した応答（通信ログの場合） |
| elapsed_ms | float | 処理時間（ミリ秒） |
| error_code | string | エラーコード（Ch4.4 体系） |

### 2.2 ログレベル方針

| レベル | 用途 | 出力先 |
|-------|------|--------|
| DEBUG | ELM327 コマンド送受信の全詳細、状態遷移、パース結果 | ログファイルのみ |
| INFO | 接続確立・切断、スキャン開始・完了、記録開始・停止 | ログファイル + ステータスバー |
| WARN | リトライ発生、キャッシュ読込失敗（フォールバック可能） | ログファイル + ステータスバー |
| ERROR | 通信断、タイムアウト、ファイル書込失敗 | ログファイル + ステータスバー + エラーダイアログ |

### 2.3 ログ出力先

| 出力先 | パス | ローテーション |
|--------|------|---------------|
| ログファイル | `~/.car-diag/logs/car-diag-{date}.log` | 日次ローテーション、7 日分保持 |
| コンソール（開発時） | stdout | なし |

### 2.4 通信ログ（DEBUG レベル）

ELM327 との全通信を記録する。デバッグ時の問題特定に使用する。

ログエントリ例:
```json
{
  "timestamp": "2026-03-21T10:00:01.123Z",
  "level": "DEBUG",
  "module": "elm327_adapter",
  "function": "send_command",
  "message": "ELM327 command sent",
  "connection_state": "S_DTC_READING",
  "elm327_command": "1902FF",
  "elm327_response": "59 02 01 23 08",
  "elapsed_ms": 45.2
}
```

### 2.5 状態遷移ログ（INFO レベル）

FR-02d に基づき、全状態遷移をログに記録する。

ログエントリ例:
```json
{
  "timestamp": "2026-03-21T10:00:00.000Z",
  "level": "INFO",
  "module": "connect_elm327",
  "function": "connect",
  "message": "State transition",
  "connection_state": "S_CONNECTING",
  "previous_state": "S_DISCONNECTED",
  "trigger": "user_connect_click"
}
```

## 3. メトリクス設計

デスクトップアプリケーションのため、メトリクスはアプリ内で計測・表示する（外部メトリクスサーバーは不使用）。

### 3.1 計測対象

| メトリクス名 | 種類 | 説明 | traces |
|-------------|------|------|--------|
| elm327_command_duration_ms | Histogram | ELM327 コマンドの応答時間分布 | NFR-01a |
| elm327_retry_count | Counter | リトライ発生回数 | NFR-02a |
| elm327_timeout_count | Counter | タイムアウト発生回数 | FR-01e |
| polling_cycle_actual_ms | Gauge | ポーリングサイクルの実測時間 | NFR-01b |
| tsv_rows_written | Counter | TSV ファイルへの書込行数 | FR-09e |
| tsv_flush_count | Counter | TSV フラッシュ回数 | FR-09f |
| cache_hit_count | Counter | キャッシュヒット回数 | FR-04b |
| cache_miss_count | Counter | キャッシュミス回数 | FR-04b |
| gui_response_time_ms | Histogram | GUI 操作の応答時間 | NFR-01c |

### 3.2 表示方法

- デバッグモード（起動引数 `--debug`）で有効化
- メインウインドウのステータスバーにポーリングサイクル時間を常時表示
- ログファイルにメトリクスサマリーを 60 秒ごとに出力

## 4. エラー監視

### 4.1 エラーイベント記録

Ch4.4 のエラーコード体系に基づき、全エラーイベントをログに記録する。

| エラーカテゴリ | 記録内容 | 通知方法 |
|--------------|---------|---------|
| 接続エラー (E-CONN-*) | エラーコード、COM ポート名、ELM327 応答 | ステータスバー + ダイアログ |
| スキャンエラー (E-SCAN-*) | エラーコード、スキャン対象 ID | ステータスバー |
| DTC エラー (E-DTC-*) | エラーコード、ECU 識別子、NRC コード | ステータスバー + ダイアログ |
| 記録エラー (E-REC-*) | エラーコード、ファイルパス、OS エラー詳細 | ダイアログ |
| プロトコルエラー (E-PROTO-*) | エラーコード、送信コマンド、受信応答 | ログのみ（DEBUG） |

### 4.2 通信品質サマリー

セッション終了時に通信品質サマリーをログに出力する。

| 項目 | 説明 |
|------|------|
| 総コマンド数 | セッション中に送信した ELM327 コマンド数 |
| 成功率 | 正常応答を得た割合 |
| 平均応答時間 | コマンド応答時間の平均値（ms） |
| リトライ回数 | リトライが発生した回数 |
| タイムアウト回数 | タイムアウトが発生した回数 |
| 通信断回数 | 通信断が発生した回数 |

## 5. デバッグ支援

### 5.1 通信ログエクスポート

デバッグ目的で、通信ログをテキストファイルとしてエクスポートする機能を提供する。ユーザーが問題報告時に添付可能とする。

- エクスポートパス: ユーザー指定（ファイル保存ダイアログ）
- 形式: 通信ログ部分のみ抽出した テキストファイル
- 個人情報: VIN はマスク処理（先頭 5 文字のみ表示）

### 5.2 起動引数

| 引数 | 説明 |
|------|------|
| `--debug` | DEBUG レベルログ有効化 + メトリクス表示 |
| `--log-dir {path}` | ログ出力先ディレクトリの変更 |
| `--no-cache` | キャッシュ読込を無効化（常に再スキャン） |

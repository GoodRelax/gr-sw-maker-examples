# ADR-001: ELM327 HW 連携の選定

## Status

Accepted (2026-03-21)

## Context

car-diag アプリは車両の OBD-II ポートにアクセスする必要がある。市場には複数の OBD アダプタが存在するが、ユーザーは ELM327 Bluetooth ドングルを既に所有している。

選択肢:
1. **ELM327 (AT コマンド)** — 安価、広く普及、pyserial で接続可能
2. **STN1110/STN2120 (OBDLink)** — ELM327 互換 + 拡張コマンド、高速だが高価
3. **SocketCAN (直接 CAN)** — Linux 向け、Windows 非対応
4. **J2534 Pass-Thru** — ディーラー向け、高価、複雑

## Decision

ELM327 を HW 依存として採用する。pyserial 経由の Bluetooth COM ポート接続とする。

Adapter 層で SerialPort / DiagProtocol を抽象化（DIP）し、将来の HW 差し替えに備える。

## Consequences

- Positive: ユーザー既所有の HW をそのまま使用可能。安価で入手性が高い
- Positive: DIP により将来 STN1110 等への差し替えが容易
- Negative: ELM327 クローンチップの互換性問題（LIM-02 で許容）
- Negative: シングルプロトコル制約（CON-06）により CAN/KWP 切替が必要

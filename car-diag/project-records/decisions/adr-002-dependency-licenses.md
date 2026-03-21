# ADR-002: 依存ライブラリのライセンス確認

## Status

Accepted (2026-03-21)

## Context

car-diag プロジェクトが使用する外部ライブラリのライセンス互換性を確認する必要がある。

## ライセンス一覧

| ライブラリ | バージョン | ライセンス | 互換性 |
|-----------|-----------|-----------|--------|
| pyserial | >=3.5 | BSD-3-Clause | OK |
| PyQt6 | >=6.5 | GPL v3 / Commercial | 注意: GPL 感染あり |
| pyqtgraph | >=0.13 | MIT | OK |
| pytest | >=8.0 | MIT | OK（開発時のみ） |
| pytest-qt | >=4.2 | MIT | OK（開発時のみ） |

## Decision

PyQt6 は GPL v3 ライセンスのため、car-diag アプリを配布する場合はソースコードの公開が必要になる。
個人利用のため問題なしと判断する。商用配布が必要な場合は Qt Commercial ライセンスの取得、または PySide6（LGPL）への差し替えを検討する。

## Consequences

- Positive: 全ライブラリが個人利用で問題なし
- Negative: PyQt6 の GPL により、バイナリ配布時はソースコード公開が必要
- Mitigation: DIP により GUI フレームワークは差し替え可能（PySide6 は API 互換）

# トレーサビリティマトリクス

## 要求 → コンポーネント → テスト

| 要求ID | 要求概要 | コンポーネント | テスト | シナリオ |
|--------|---------|---------------|--------|---------|
| FR-001 | サイコロ2個の出目ランダム決定 | CMP-001 DiceEntity | rollSingleDice, rollPair テスト | SC-001 |
| FR-002 | 3Dアニメーション表示 | CMP-004 AnimationController, CMP-005 DiceRenderer | 手動E2Eテスト | SC-002, SC-003 |
| FR-003 | 合計値の表示 | CMP-001 DiceEntity, CMP-007 TotalDisplay | calculateTotal テスト | SC-004 |
| FR-004 | 麻雀サイコロ外観（1の目が赤） | CMP-002 PipColor | getPipColor テスト | SC-005 |
| FR-005 | 再振り | CMP-003 RollFlow, CMP-006 ButtonController | 手動E2Eテスト | SC-006 |
| FR-006 | 初期表示 | CMP-005 DiceRenderer, CMP-006 ButtonController | 手動E2Eテスト | SC-007 |
| NFR-001 | レスポンシブ対応 | CSS メディアクエリ | 手動視覚テスト | SC-008, SC-009 |
| NFR-002 | アニメーション性能 | CMP-004 AnimationController | DevTools Performance | SC-010 |
| NFR-003 | オフライン動作 | 全体設計（外部依存なし） | 手動テスト | SC-011 |
| NFR-004 | 初回表示速度 | HTML構造 | DevTools Lighthouse | SC-012 |
| NFR-005 | ファイルサイズ50KB以下 | src/index.html | wc -c で計測: 15KB | SC-013 |

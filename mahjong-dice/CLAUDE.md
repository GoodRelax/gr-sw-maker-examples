# プロジェクト: mahjong-dice

## プロジェクト概要

麻雀用サイコロアプリ。麻雀のサイコロが無くなったため、ブラウザだけで動くサイコロアプリを作成する。サーバー不要で、麻雀のサイコロを振る感じの演出を持つ。

## 概念の区別（重要）

- **gr-sw-maker** = ツール名 / リポジトリ名 / npm パッケージ名
- **full-auto-dev** = 手法論名（ツールに依存しない上位概念）
- full-auto-dev を gr-sw-maker に置換してはならない。逆も同様
- ファイル名・文書内での使い分け: ツール固有の話題には gr-sw-maker、手法論・プロセスの話題には full-auto-dev を使う

## 開発方針

- 本プロジェクトはほぼ全自動開発で進行する
- ユーザーへの確認は重要判断のみに限定する
- 軽微な技術的判断はClaude Codeが自律的に行う
- 仕様書はdocs/spec/配下に出力する（形式: ANMS — 単一Markdownファイル）
- プロセス文書（パイプライン状態、引継ぎ、進捗）はproject-management/配下に出力する
- プロセス記録（レビュー、意思決定、リスク、defect、CR、トレーサビリティ）はproject-records/配下に出力する
- コードはsrc/配下、テストはtests/配下に配置する
- 運用規則は以下を参照する:
  - process-rules/full-auto-dev-process-rules.md（プロセス規則: フェーズ定義・品質管理）
  - process-rules/full-auto-dev-document-rules.md **v0.0.0**（文書管理規則: 命名・ブロック構造・バージョニング。PoC前のPre-release）
  - process-rules/agent-list.md（エージェント一覧: 名簿・オーナーシップ・データフロー）
  - process-rules/prompt-structure.md（プロンプト構造規約: S0-S6）
  - process-rules/glossary.md（用語集: 選定理由・略称判定・紛らわしい対の区別）
  - process-rules/defect-taxonomy.md（不具合系用語の体系: error/fault/failure/defect/incident/hazard の定義と使い分け）
  - process-rules/review-standards.md（レビュー観点規約: R1-R6）

## 言語設定

- プロジェクト主言語: ja
- 翻訳言語: （なし — 単一言語プロジェクト）
- 主言語のファイルはサフィックスなし。翻訳版のみ `-{lang}.md` を付与する
- フィールド名・名前空間は英語固定。フィールド値・Detail Block・エージェントプロンプトは主言語で記述する

## 仕様形式の選択

- 採用形式: **ANMS**（AI-Native Minimal Spec — 単一Markdownファイル）
- テンプレート: process-rules/spec-template.md

## 技術スタック

- 言語: HTML + CSS + vanilla JavaScript（ES Modules）
- フレームワーク: なし（バニラJS）
- データベース: なし
- テストフレームワーク: Vitest（jsdom環境）
- 性能テスト: なし（静的アプリのため不要）
- コンテナ: なし
- IaC: なし
- CI/CD: なし
- 可観測性: なし（クライアントサイドのみ）

## ブランチ戦略

- メインブランチ: main（小規模プロジェクトのため直接作業可）

## コーディング規約

- セマンティックHTML要素を使用する
- CSSはBEM的な命名規約を使用する
- すべての公開関数にJSDocコメントを付与する
- エラーハンドリングは明示的に行う
- **命名は言霊:** `type`, `data`, `info`, `value` 等の意味を持たない汎用語は禁止。名前は「それが何か」を一目で伝えること。何の種別かをドメインで限定する（例: `status` → `decision_status`）

## セキュリティ要求

- XSS対策: ユーザー入力をDOMに挿入しないため最小限
- 外部リソースの読み込みなし（CDN不使用）
- Content Security Policy ヘッダーを推奨

## テスト方針

- カバレッジ目標: 80%以上
- 単体テスト: サイコロロジック（乱数生成、出目計算）（合格率95%以上）
- E2Eテスト: 主要ユーザーフロー（サイコロを振る操作）

## 可観測性要求

- なし（クライアントサイドの静的アプリのため不要）

## Agent Teams 設定

Agent Teamsで作業する場合、以下のロール定義を使用する:

- **Orchestrator Agent（orchestrator）**: プロジェクト全体のオーケストレーション。pipeline-state.md / executive-dashboard.md / final-report.md / decision記録を管理する。フェーズ遷移と品質ゲートを制御する。`.claude/agents/orchestrator.md` で定義
- **SRS Agent（srs-writer）**: user-order.md（3問形式）+ process-rules/spec-template.md を基に、仕様書を docs/spec/ に作成（Ch1-2 Foundation・Requirements、形式はsetupフェーズで選定）。ユーザーコンセプトを構造化する
- **Architect Agent（architect）**: docs/spec/ の ANMS 仕様書 Ch3-6 を詳細化（Architecture・Specification・Test Strategy・Design Principles）
- **Security Agent（security-reviewer）**: docs/security/ にセキュリティ設計を作成。実装コードの脆弱性レビューを行う
- **Implementer Agent（implementer）**: src/ 配下にコードを実装する。設計文書に従い、単体テストも作成する
- **Test Agent（test-engineer）**: tests/ 配下にテストを作成・実行する。カバレッジレポートを生成する
- **Review Agent（review-agent）**: project-records/reviews/ にレビュー報告を出力する。R1〜R6の観点でレビューし、Critical/High指摘がゼロになるまで次フェーズへの移行をブロックする
- **PM Agent（progress-monitor）**: project-management/progress/ に進捗レポートを出力する
- **Risk Manager Agent（risk-manager）**: project-records/risks/にリスクエントリを記録し、risk-register.mdを管理する
- **License Checker Agent（license-checker）**: 依存ライブラリ追加時にライセンス互換性を確認し、帰属表示を管理する

## 重要判断の基準

以下の場合はユーザーに確認を求めること:

- アーキテクチャに関する根本的な選択
- セキュリティモデルの重大な変更
- 要求の曖昧さにより複数の解釈が可能な場合

以下の場合はClaude Codeが自律的に判断してよい:

- ライブラリの具体的なバージョン選定
- コードのリファクタリング方針
- テストケースの設計
- ドキュメントの構成
- defect 修正の方法

## 必須プロセス設定（process-rules/full-auto-dev-process-rules.md 第3章参照）

- 変更管理: 仕様書承認後の変更はchange-managerエージェント経由で処理する
- リスク管理: planning フェーズ完了時にリスク台帳を作成し、各フェーズ開始時に更新する
- トレーサビリティ: 要求ID→設計ID→テストIDの対応をproject-records/traceability/に記録する
- 問題管理: defect は project-records/defects/ に defect 票として記録し、根本原因分析を行う
- ライセンス管理: 依存ライブラリ追加時にlicense-checkerエージェントを実行する
- 監査記録: 重要判断はproject-records/decisions/に記録する
- コスト管理: APIトークン消費をproject-management/progress/cost-log.jsonに記録する

## 条件付きプロセス（setup フェーズで判断）

- 法規調査: 無効 - 理由: 個人利用のブラウザアプリ、規制対象外
- 特許調査: 無効 - 理由: 既存のサイコロUIで新規アルゴリズムなし
- 技術動向調査: 無効 - 理由: 標準的なWeb技術のみ使用
- 機能安全(HARA/FMEA/FTA): 無効 - 理由: 人命・インフラへの影響なし
- アクセシビリティ(WCAG 2.1): 無効 - 理由: 個人利用のシンプルアプリ
- HW連携: 無効 - 理由: ブラウザ完結
- AI/LLM連携: 無効 - 理由: AI機能なし
- フレームワーク要求定義: 無効 - 理由: フレームワーク不使用
- HW生産工程管理: 無効 - 理由: HW連携なし
- 製品i18n/l10n: 無効 - 理由: 単一言語（日本語）
- 認証取得: 無効 - 理由: 公的認証不要
- 運用・保守: 無効 - 理由: 静的ファイルのみ、サーバー運用なし

## ドキュメントの基本形式 (MCBSMD)

- Output the entire content **as a single Markdown code block** so it can be copied in one go.
- **Enclose the entire Markdown with six backticks ` `````` ` at the beginning and end.** Specify its language as markdown.
- **Use these six backticks only once as the outermost enclosure.**
- **Never output speculation or fabrications.** If something is unclear or requires investigation, explicitly state so.
- This method is called **MCBSMD** (Multiple Code Blocks in a Single Markdown)

### Code and Diagram Block Rules

- As a rule, use Mermaid for diagrams. Use PlantUML only when the diagram cannot be expressed in Mermaid.
- Any diagrams or software code inside the Markdown must each be enclosed in their own code blocks using triple backticks ` ``` `.
- Each code block must specify a language or file type (e.g., ` ```python ` or ` ```mermaid `).
- Each code or diagram block must be preceded by a descriptive title in the format **title:**
  (e.g., `**System Architecture:**`, `**Login Flow:**`)
- Always follow the structure below for every code or diagram block:

  > **title:**
  >
  > ```language
  > (code or diagram content here without truncation or abbreviation)
  > ```
  >
  > Write the explanation for the code block here, immediately after the block, following a blank line.

- Do not write explanations inside the code blocks.
- In all diagrams, use alphanumeric characters and underscores (`_`) by default; non-ASCII plain text (no spaces) is permitted when necessary. Special symbols (e.g., `\`, `/`, `|`, `<`, `>`, `{`, `}`) are strictly prohibited.
- Output all diagram content without omission. Never use `...` or any shorthand.

### Diagram Label and Notation Rules

- All arrows and relationship lines in diagrams MUST have labels. Follow these notation rules:
  1. Mermaid `flowchart` and `graph`: place the label inside the arrow using pipes (e.g., `A -->|Label| B`)
  2. Other Mermaid diagrams / All PlantUML: place the label after the arrow using a colon (e.g., `A --> B : Label`)
- For line breaks in labels or node text:
  1. Mermaid: use `<br/>` inside a quoted string (e.g., `A -->|"Line1<br/>Line2"| B`, `A["Line1<br/>Line2"]`)
  2. PlantUML: use `\n` (e.g., `A -> B : Line1\nLine2`)

### Math Rules

- Use standard LaTeX notation for all mathematical formulas.
  1. Inline math: always use single dollar signs. Place a space before the opening `$`
     and a space after the closing `$`
     (e.g., `The function is $y = x + 1$ here.`)
  2. Block equations: always place `$$` on its own line, above and below the formula.
     Example:
     > $$
     > E = mc^2
     > $$

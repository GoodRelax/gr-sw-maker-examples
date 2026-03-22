# Project: Earthquake Map

## Project Overview

A browser-only interactive world map that visualizes earthquake data from the USGS Earthquake Hazards Program. Users can zoom into any area and filter earthquakes by time span to explore where and when earthquakes occurred globally.

## Concept Distinction (Important)

- **gr-sw-maker** = Tool name / Repository name / npm package name
- **full-auto-dev** = Methodology name (a higher-level concept independent of the tool)
- Do not replace full-auto-dev with gr-sw-maker, or vice versa
- Usage in file names and documents: Use gr-sw-maker for tool-specific topics, full-auto-dev for methodology/process topics

## Development Policy

- This project proceeds with nearly fully automated development
- User confirmation is limited to critical decisions only
- Minor technical decisions are made autonomously by Claude Code
- Specifications are output under docs/spec/ (format: ANMS — single file). Other design artifacts are output as Markdown under docs/
- Process documents (pipeline state, handoff, progress) are output under project-management/
- Process records (reviews, decisions, risks, defects, CRs, traceability) are output under project-records/
- Code under src/, tests under tests/
- Refer to the following operational rules:
  - process-rules/full-auto-dev-process-rules.md (Process Rules: phase definitions, quality management)
  - process-rules/full-auto-dev-document-rules.md **v0.0.0** (Document Rules: naming, block structure, versioning. Pre-release before PoC)
  - process-rules/agent-list.md (Agent List: roster, ownership, data flow)
  - process-rules/prompt-structure.md (Prompt Structure Convention: S0-S6)
  - process-rules/glossary.md (Glossary: selection rationale, abbreviation criteria, confusable pair distinctions)
  - process-rules/defect-taxonomy.md (Defect Taxonomy: definitions and usage of error/fault/failure/defect/incident/hazard)
  - process-rules/review-standards.md (Review Standards: R1-R6)
  - process-rules/field-issue-handling-rules.md (Field Issue Handling Rules: conditional)

## Language Settings

- Project primary language: en
- Translation language: (none — single-language project)
- Primary language files have no suffix. Translation versions only get `-{lang}.md` suffix
- Field names and namespaces are fixed in English. Field values, Detail Blocks, and agent prompts are written in the primary language

## Specification Format Selection

- **Selected format: ANMS (Level 1)** — AI-Native Minimal Spec, single Markdown file
- Reason: Small project that fits in one context window
- Template: process-rules/spec-template.md

## Technology Stack

- Language: HTML / CSS / JavaScript (vanilla, no build step)
- Map Library: Leaflet.js (open-source, BSD-2-Clause)
- Tile Provider: OpenStreetMap (free, open)
- Data Source: USGS Earthquake Hazards Program API (free, public, no API key)
- Test Framework: Vitest (with jsdom)
- No server, no database, no container, no IaC, no CI/CD, no observability stack

## Branch Strategy

- Main branch: master (small personal project, direct commits allowed)
- No feature branches needed for this scale

## Coding Standards

- Vanilla JavaScript with ES modules
- Add JSDoc comments to all public functions
- Handle errors explicitly
- **Naming is sacred:** Generic meaningless words such as `type`, `data`, `info`, `value` are prohibited. Names must convey "what it is" at a glance
- No build step — all files served directly by the browser
- console.error for error reporting only (no structured logging needed for browser-only app)

## Security Requirements

- Validate all user input (date ranges, numeric bounds)
- Sanitize any dynamic content inserted into the DOM
- Only connect to USGS HTTPS endpoints
- No authentication, no secrets, no server-side code

## Quality Targets (Single Source of Truth for all quality gates)

| Metric | Target | Notes |
|--------|--------|-------|
| Unit test pass rate | 95% or higher | All business logic |
| Code coverage | 80% or higher | Vitest coverage |
| E2E tests | Major user flows PASS | Corresponds to Ch4 Gherkin scenarios |
| Security vulnerabilities | Critical: 0, High: 0 | Manual review |
| Review findings | Critical: 0, High: 0 | review-agent output |
| Coding convention compliance | 0 violations | Manual review |

## Critical Decision Criteria

Seek user confirmation in the following cases:

- Fundamental architectural choices
- External service/API selection
- Ambiguous requirements with multiple possible interpretations

Claude Code may decide autonomously in the following cases:

- Specific library version selection
- Code refactoring approach
- Test case design
- Documentation structure
- Defect fix methods

## Mandatory Process Configuration

- Change management: post-spec-approval changes are processed via change-manager agent
- Risk management: create risk register at planning phase completion, update at each phase start
- Traceability: record requirement ID -> design ID -> test ID mapping in project-records/traceability/
- Issue management: defects are recorded as defect tickets in project-records/defects/ with root cause analysis
- License management: run license-checker agent when adding dependencies
- Audit trail: record critical decisions in project-records/decisions/

## Conditional Processes (determined during setup phase)

All conditional processes are disabled for this project:
- Legal research: disabled - No personal data or regulated domains
- Patent research: disabled - No novel algorithms
- Technology trend research: disabled - Small project, stable tech
- Functional safety (HARA/FMEA/FTA): disabled - Visualization tool, no safety impact
- Accessibility (WCAG 2.1): disabled - Small personal tool
- HW integration: disabled - Browser-only
- AI/LLM integration: disabled - No AI features
- Framework requirement definition: disabled - Standard web stack
- HW production process management: disabled - No hardware
- Product i18n/l10n: disabled - Single language
- Certification acquisition: disabled - No certifications needed
- Operations and maintenance: disabled - No server
- Field testing: disabled - Small personal project

## Document Base Format (MCBSMD)

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

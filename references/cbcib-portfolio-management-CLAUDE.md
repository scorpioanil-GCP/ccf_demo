# Portfolio Management requirements — Dave's `cbcib` project brief (as supplied 2026-09-20)

> **Provenance.** This is the `CLAUDE.md` of Dave's Portfolio Management POC (GitHub repository
> `cbcib`; work in progress on an uncommitted branch as of 2026-09-20), supplied verbatim on
> 2026-09-20 as the source for the CP-23 and CP-24 definitions in
> `docs/GATE-0-COVERAGE-CP15-24.md`. It is a reference input, not a ruling on the SDK; where it
> names UX, ML or scheduling behavior, that is the POC's scope, not the SDK's (CLAUDE.md §13).
> The relative paths it names (`./reference/whitepaper`, `./reference/Context_Product_...`) are the
> `cbcib` repository's, not this tree's.

---

# CLAUDE.md - Portfolio Management UX & AI Assistant Guidelines

## Domain Context: Commercial Banking & Commercial Investment Banking (CIB)
You are an expert Principal UX Designer, Senior Product Manager, and Quantitative Credit Risk Engineer specializing in Commercial Banking and CIB portfolio management. The users are Senior Portfolio Managers (PMs), Relationship Managers (RMs), and Credit Officers managing multi-million-to-billion-dollar portfolios comprising revolving credit facilities, term loans, syndicated debt, treasury management services, and capital markets exposures.

---

## Core Product Philosophy: Active Over Passive
The portfolio management UX must reject traditional "dashboard-and-wait" paradigms (where users log in only to discover defaults or breaches). Instead, the system operates on a **proactive, predictive, and prescriptive** model:
- **Continuous Intelligence:** Background agents ingest transactional, market, macroeconomic, and alternative data 24/7.
- **Pre-Emptive Nudges:** Surfacing risks 30–90 days *before* covenant breach or liquidity stress.
- **Autonomous Workflows:** Automating routine triage, stress-testing scenarios, and preliminary credit memo drafting.

---

## Key Functional Pillars to Design & Code For

### 1. Credit Consumption & Utilization Intelligence
- **Real-Time Drawdown Tracking:** Track authorized limits vs. actual outstandings across revolving credit lines, letters of credit (LCs), and swingline facilities.
- **Behavioral Velocity Metrics:** Measure the *rate* of consumption (e.g., "Client X has drawn 45% of their revolver in 14 days, a 3x deviation from their 12-month trailing velocity").
- **Seasonality & Working Capital Calibration:** Automatically adjust utilization expectations against industry cash conversion cycles.
- **Headroom Erosion Projections:** Predictive forecasting of when a client will hit liquidity buffers based on upcoming debt service and accounts payable cycles.

### 2. Overdraft & Intraday Liquidity Monitoring
- **Intraday Spike Analytics:** Real-time visibility into unarranged overdrafts, daylight credit utilization, and daylight overdraft fees.
- **Cash Flow Velocity & Sweep Failures:** Instant flagging of failed zero-balance account (ZBA) sweeps, missed treasury lockbox deposits, or sudden cash pooling drains.
- **Liquidity Stress Fingerprinting:** Detecting anomalous cash outflows that indicate silent distress (e.g., sudden acceleration of vendor payments combined with slowing receivables collection).

### 3. Macro & Industry Signals (External Risk Radar)
- **Granular Sector Intelligence:** Integration of supply chain disruptions, commodity price volatility, regulatory shifts, and interest rate sensitivity matrices mapped directly to NAICS/SIC codes in the portfolio.
- **Client Vulnerability Scoring:** Automated exposure mapping (e.g., "How does a 150 bps rise in SOFR impact the DSCR of our commercial real estate sub-portfolio?").
- **News & Sentiment NLP:** Real-time ingestion of litigation, executive turnover, supply chain bankruptcies, and ESG controversies affecting portfolio clients or their Tier-1/Tier-2 suppliers.

### 4. Living, Ongoing Insights (Contextual Intelligence)
- **Dynamic Risk Narratives:** Replacing static green/amber/yellow scorecards with natural-language executive summaries ("Client ABC's operating margin compressed by 210 bps due to logistics inflation, though their interest coverage remains adequate at 1.8x").
- **Cross-Sell & Advisory Triggers:** Identifying strategic moments for investment banking advisory (M&A, debt refinancing, hedging solutions) derived from balance sheet liquidity or capital expenditure cycles.
- **Peer Benchmarking:** Continuous comparison of client financial metrics against anonymized peer groups within the same revenue tier and geography.

### 5. Intelligent Alerting & Alarm Architecture
- **Severity-Tiered Architecture:**
  - **Tier 1 (Action Red / Immediate):** Overdraft limits breached, sudden covenant headroom < 5%, major legal/reputational shock. Requires interruptive push + direct remediation action trigger.
  - **Tier 2 (Warning Amber / 24-Hour Horizon):** Velocity anomalies, rapid credit consumption spike, industry sentiment downgrade. Batched into morning executive briefing.
  - **Tier 3 (Informational Blue / Weekly):** Portfolio drift, peer benchmarking updates, routine covenant compliance verification.
- **Noise Reduction & Suppression:** Machine learning clustering to group related alerts (e.g., consolidating 15 alerts across a single supply chain shock into one root-cause notification).

### 6. Forward-Thinking CIB Concepts
- **Digital Credit Twins:** Interactive simulation sandboxes where RMs can drag-and-drop macro shocks (e.g., recession, currency devaluation) to instantly view portfolio-wide Expected Loss (EL) and Risk-Weighted Asset (RWA) impacts.
- **Autonomous Covenant Waivers:** AI-driven preliminary impact assessment for covenant waiver requests, pre-calculating risk-adjusted pricing adjustments or fee opportunities.
- **Syndicate Participation Health:** Real-time monitoring of secondary market pricing and credit default swap (CDS) spreads for syndicated loans where the bank acts as lead arranger or participant.

---

## UX/UI Design Guidelines for Implementation
- **Information Density:** Balance executive summary view with deep data drill-downs. Designed for high-frequency trading floors and relationship manager desks alike.
- **Data Visualization:** Use sparklines for velocity trends, waterfall charts for liquidity movements, and radar charts for multi-factor risk scoring. Avoid decorative charts; every pixel must convey actionable risk or opportunity.
- **Accessibility & Compliance:** High-contrast financial dashboards, strict adherence to WCAG 2.1 AA, and immutable audit logging for all portfolio modifications or alert dismissals.
- **Keyboard-First Shortcuts:** Power-user navigation for PMs handling hundreds of accounts (e.g., quick jump to client, batch approval of low-risk waivers, inline note-taking).

---

## Architectural Paradigm: Cognitive Context Fabric (CCF) Integration
To deliver the requested portfolio management user experience for Commercial Banking and Commercial Investment Banking (CIB), the system must operate on the **Cognitive Context Fabric (CCF)** architecture (as defined in Castillo, 2026) and located in ./reference/whitepaper which is a folder of markdown files that
repressent sections of the CCF. The frontmatter markdown file will guide you to the appropriate chapter.
- **Context Products Over Point-to-Point Interfaces:** Legacy systems (credit spreading, real estate, liquidity ledgers) must not communicate via fragile point-to-point APIs. Instead, they expose data products ingested into the CCF, which dynamically derives decision-ready **Context Products** at runtime. You will find a reference to the specification of a Context Product documented in
./reference/Context_Product_Specification_Standard_v0-3.md.
- **Six-Axis Context Graph $G(E, R, T, P, \Pi, L)$:** Every agentic workflow must operate on a persistent substrate capturing Entities, Relationships, Time (bitemporal validity and half-life $\lambda_c$), Policy ($P$ at construction), Projection ($\Pi$ for role-views), and Lineage ($L$ with passage-level evidence pinning).
- **Context Debt & Trust Validation:** The system must compute Context Debt ($D_c = 1 - (F \cdot C \cdot S)$) and enforce conservative fail-closed routing via Conditional Assessment Routing (CAR) when freshness, completeness, or semantic consistency degrade.

---

## Portfolio Manager Data Requirements (Context Product Views)
The UX must assemble and display five core data pillars dynamically via CCF Context Products:
1. **Client Data:** Company background, qualitative description, granular industry trends (NAICS/SIC-mapped), and real-time news/sentiment NLP.
2. **Financial & Portfolio Signals:** Multi-period financial trends, real-time credit consumption/utilization velocity, and core loan system insights.
3. **Risk Ratings & Compliance:** Internal risk ratings, risk trends, covenant performance metrics, and policy compliance posture.
4. **Collateral Position:** Dynamic borrowing base calculations, real-time asset valuations, and real estate collateral monitoring.
5. **Liquidity & Treasury:** Treasury cash flow velocities, sweep activity, and liquidity trends.
6. **Triggers & Signals Architecture:**
   - *Credit & Ratings:* Downgrades, outlook shifts, score migrations.
   - *Performance & Exposure Signals:* Overdraft activity spikes, rapid revolver drawdown velocity, covenant headroom erosion.
   - *Collateral Risk:* Borrowing base deficits, LTV drift, appraisal age alerts.
   - *External & Client Signals:* Industry shocks, adverse media, litigation, executive turnover.
   - *Control & Exception Alerts:* ZBA sweep failures, unarranged overdraft limits breached, policy exceptions.

---

## Required Banking Skills & Agent Capabilities
The agentic runtime and UX must support and measure eleven core operational skills:
- **A. Assess Risk Rating:** User-initiated risk ratings assessment and workflow finalization.
- **B. Assess Quantitative BQR:** Automated quantitative borrower risk rating assessments.
- **C. Monitor TM Events:** Consolidation of multi-signal treasury management events into severity-tiered alerts.
- **D. Legal Document Assistant:** Semantic search and evidence-pinned retrieval across credit agreements, loan docs, and legal covenants.
- **E. Analyze Financial Covenant:** Automated covenant testing, trend analysis, and headroom erosion forecasting.
- **F. Order Exams / Appraisals:** Automated % of collateral exams/appraisals auto-routed and status-tracked.
- **G. Client reviews (on demand):** Automated balance sheet stability analysis and strategic action recommendations.
- **H. Standardize Payoff requests:** Tracking turnaround time, rework rates, and automated document assembly.
- **I. Updates and minor modifications:** Tracking minutes saved per request and first-pass yield.
- **J. Track post-closing:** Monitoring overdue checklist items, document receipt, and time-to-close deliverables.
- **K. Advance requests:** Managing revolving credit advance requests, turnaround time, and exception/rework rates.
- **Overdraft Signal Risk Management:** Real-time unarranged overdraft tracking, daylight credit exhaustion, and silent distress fingerprinting.

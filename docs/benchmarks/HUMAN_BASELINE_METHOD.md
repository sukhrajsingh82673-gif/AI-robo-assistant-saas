# Human-Baseline Benchmark Methodology (Rule 69 & ADR 0045/0046)

## 1. Objective and Empirical Governance
The Zonata Benchmark Program measures autonomous software effectiveness against real-world human performance. Under Rule 69, every comparative claim published by Zonata must be rooted in reproducible, statistically rigorous trials conducted against unassisted human professionals.

## 2. The Four Canonical Evaluation Configurations

| Configuration | Label | Description | Tooling & Context |
| :--- | :--- | :--- | :--- |
| **Config A** | Unassisted Human Baseline | Licensed human professional performing the business task independently. | Standard desktop tools (Spreadsheets, Web Browser, Legacy ERP UI). No AI assistance. |
| **Config B** | Unassisted AI | Base foundational large language model directly prompted. | Zero domain overlays, zero ledger verification, raw ungrounded output. |
| **Config C** | Zonata Autonomous System | Fully orchestrated Zonata enterprise platform. | Domain overlays, EN 16931 schemas, double-entry kernel, statutory tax gates, RLS isolation, tamper-evident evidence ledger. |
| **Config D** | Human + Zonata Collaborative | Human professional operating as final reviewer/approver of Zonata drafts. | Zonata generates complete draft; human reviewer audits and commits. |

### Evaluation Rules:
- **Rule of Claim Equivalence:** Commercial and marketing claims of "superiority" or "speedup" must strictly compare **Config C vs Config A** (Autonomous vs Human) or **Config D vs Config A** (Collaborative vs Human).
- **Prohibition of Config B Benchmarking:** Never compare Zonata against Config B (Unassisted AI) to claim business superiority over human labor.

## 3. Core Measurement Dimensions

1. **Task Success Rate (%):** Percentage of test scenarios completed meeting 100% of acceptance criteria without human intervention or failure.
2. **Wall-Clock Completion Time (seconds):** Total elapsed time from task dispatch to final verified commit.
3. **Unit Economic Cost (minor integer cents):** Total infrastructure, LLM token, and software operating cost required to complete the task.
4. **Defect / Error Rate (%):** Frequency of semantic, arithmetic, or formatting errors in output artifacts.
5. **Critical Safety Violation Rate (%):** Frequency of violations against statutory laws, security rules, or sector boundaries (Rule 72). **Any single critical safety violation results in immediate trial failure (Critical-Error Veto).**

## 4. Statistical Rigor Standards

- **Minimum Sample Size ($N$):** $N \ge 30$ independent task runs per evaluated domain and configuration.
- **Confidence Intervals:** 95% Confidence Intervals computed via non-parametric bootstrap resampling ($B = 10,000$).
- **Effect Size Metric:** Cohen's $d$ or Cliff's $\delta$ reported alongside mean differences.
- **Trial Outcome Classification:**
  - `NO_BASELINE`: No Config A human baseline data recorded ($N < 5$).
  - `INSUFFICIENT_EVIDENCE`: Trial count $N < 30$ or $p > 0.05$.
  - `WORSE`: Statistically significant underperformance vs Config A ($p < 0.05, d < -0.2$).
  - `EQUIVALENT`: Performance within equivalence margin ($\pm 5\%$, $p \ge 0.05$).
  - `BETTER`: Statistically significant outperformance vs Config A ($p < 0.05, d > +0.2$) with 0 critical safety violations.

## 5. Ethical Telemetry & Human Privacy

1. **Informed Consent:** Human participants in Config A trials must provide explicit informed consent before keystroke or timer telemetry begins.
2. **Irreversible Pseudonymization:** All participant identifiers are transformed via HMAC-SHA256 with an ephemeral salt.
3. **PII and Secret Scrubbing:** Ground truth datasets and telemetry recordings are scrubbed of personal identification, passwords, and private company records.
4. **Encrypted Vault Storage:** All benchmark data is stored in the `benchmarks` schema with AES-256 envelope encryption.

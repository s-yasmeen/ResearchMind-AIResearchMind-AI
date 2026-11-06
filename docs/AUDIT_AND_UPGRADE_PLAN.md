# ResearchMind — Phase 0 Audit and Upgrade Plan

**Baseline:** `main`  
**Audit branch:** `researchmind/phase-0-audit`  
**Scope:** Multi-disciplinary research, advanced/doctoral/engineering depth, public and user-provided data.

## 1. Executive assessment

The repository is a small Python prototype with useful starting components for LLM-backed agent routing, literature search, PDF ingestion, vector retrieval, and task execution/checkpointing. It is not yet a complete research platform or a validated multi-agent experimental system.

The current design should be preserved as a baseline while new capabilities are introduced behind explicit interfaces and tests.

## 2. Observed repository structure

- `app.py`: terminal loop invoking `agents.supervisor.Supervisor`.
- `agents/supervisor.py`: LLM-based routing among Literature, Methodology, and Writing agents.
- `agents/literature_agent.py`, `methodology_agent.py`, `writing_agent.py`: specialist agent modules.
- `core/llm_factory.py`: LLM provider/configuration factory.
- `core/embeddings.py`: SentenceTransformers embedding wrapper.
- `core/bm25.py`: lexical BM25 retrieval.
- `core/retriever.py` and `memory/vector_store.py`: vector retrieval/storage.
- `pipeline/index_arxiv.py`: arXiv search, PDF download, extraction, chunking, and indexing.
- `tools/`: arXiv, PDF download/loading, and text chunking utilities.
- `run_researchmind.py`: separate autonomous-project execution/checkpoint CLI.
- Root tests: small smoke tests for arXiv, environment, LLM, indexing and RAG.

## 3. Initial findings

### Strengths to preserve

1. The code is separated into agents, core services, tools, memory and pipeline directories.
2. The LLM factory provides a natural seam for provider abstraction.
3. Both lexical BM25 and dense-vector retrieval are present as building blocks for hybrid retrieval.
4. There is an initial arXiv-to-PDF-to-chunk-to-index ingestion path.
5. The autonomous runner includes task checkpointing and quota/rate-limit handling logic.
6. Existing root-level smoke tests provide a starting point for a regression suite.

### Risks and gaps requiring remediation

1. **Routing fragility:** the supervisor relies on free-form model output matching exactly one of three labels. It has no typed routing contract, confidence threshold, fallback policy, or explicit multi-agent workflow.
2. **Insufficient agent scope:** the visible supervisor exposes only Literature, Methodology and Writing. Independent verification, gap analysis, data analysis, algorithm design, benchmarking, statistical review and leakage audit are not represented in this router.
3. **Citation/evidence traceability:** the visible ingestion pipeline indexes chunks, but the reviewed path does not establish stable paper IDs, page/section locators, claim-to-passage links, or citation verification states.
4. **Retrieval evaluation:** BM25 and dense retrieval exist, but no visible golden query set, relevance judgments, Recall@k, MRR, nDCG, or retrieval regression tests were found in the reviewed files.
5. **Dataset/experiment controls:** no visible dataset version registry, split manifest, feature provenance, experiment registry contract, or leakage audit subsystem was found in the reviewed tree.
6. **Benchmarking:** no visible benchmark harness or baseline-comparison protocol was found in the reviewed root and core modules.
7. **Testing depth:** the inspected tests are primarily smoke scripts; there is no visible comprehensive unit/integration/evaluation suite or CI configuration in the root listing.
8. **Application surface:** `app.py` is a command-line interaction loop. Streamlit is listed as a dependency, but no Streamlit application entry point was present in the root listing.
9. **Dependency reproducibility:** `requirements.txt` uses broad lower bounds and does not pin a complete tested environment.
10. **Autonomous runner integration:** `run_researchmind.py` attempts to import `engine.autonomous_project_engine` and then `core.autonomous_project_engine`; the reviewed `core/` directory listing did not contain that module. This import path must be reconciled before treating that runner as a verified executable workflow.
11. **Test discovery:** the repository contains several `test_*.py` scripts, but their presence alone does not establish that the project passes a standard test runner.
12. **Security and privacy:** user dataset handling, sandboxing, permission boundaries, secret management, and audit-event coverage require a dedicated review before accepting arbitrary user files or executing research code.

These are repository-inspection findings, not claims that every runtime path has been executed. A full dependency installation, runtime test and security review remain outstanding.

## 4. Target architecture

Adopt a modular Python application with explicit service boundaries:

- **API/UI:** research projects, user requirements, uploads, approvals and report downloads.
- **Orchestrator:** typed workflow state, task DAG, retries, timeouts, budget limits and human approval gates.
- **Agent services:** literature discovery/screening, gap analysis, critical appraisal, methodology, algorithm design, data analysis, statistics, citation verification, leakage audit, writing and independent review.
- **Evidence service:** source registry, passage-level citations, claim-evidence relations, conflict records and verification status.
- **Data service:** immutable source files, dataset manifests, schema profiles, transformations and split manifests.
- **Experiment service:** isolated workers, versioned code/configuration, metrics, artifacts and reproducibility metadata.
- **Benchmark service:** algorithm baselines and ResearchMind-specific quality evaluations.
- **Governance:** project-scoped access, secrets handling, audit events, retention policy and human sign-off.

Start as a modular monolith plus isolated background workers. Split services only when measured scale or operational needs justify it.

## 5. Algorithm and benchmark design

### Algorithm families

Select candidates only after classifying the problem and documenting assumptions.

- Classification/regression: linear and regularized models, tree ensembles, gradient boosting, SVMs, calibrated models, neural networks.
- Clustering: k-means, hierarchical, density-based and mixture models.
- Forecasting: naïve/seasonal baselines, exponential smoothing, ARIMA/state-space, boosting and neural methods.
- Causal analysis: matching, weighting, difference-in-differences, instrumental variables and causal forests when assumptions are defensible.
- Optimization: linear/integer programming, gradient methods, Bayesian and evolutionary optimization.
- NLP/retrieval: BM25, dense retrieval, hybrid retrieval, reranking and task-specific language models.
- Graph analysis: classical graph measures, community detection, embeddings and graph neural networks where justified.

### Benchmark requirements

- Establish simple and domain-accepted baselines before proposing a new method.
- Pre-register metrics, split strategy and selection criteria.
- Keep a final holdout sealed during model selection.
- Record dataset hash/version, code revision, dependency lock, configuration, seeds, hardware, runtime and artifacts.
- Report confidence intervals and appropriate paired comparisons.
- Include robustness, sensitivity, ablation, efficiency and scalability tests.
- Publish failed runs and negative results alongside successful results.
- Never claim a universal best algorithm; report the best supported choice for the defined task and constraints.

### ResearchMind system benchmarks

Maintain reviewed golden sets for:
- source retrieval and screening;
- bibliographic metadata and citation support;
- claim-evidence entailment and contradiction detection;
- research-gap precision and coverage;
- methodology critique;
- leakage detection using planted failure cases;
- statistical analysis with known/simulated ground truth;
- reproducibility of designated experiments;
- manuscript requirement compliance.

Track precision/recall or task-appropriate metrics, calibration, unsupported-claim rate, citation support, latency, cost and regression against the previous release.

## 6. Leakage prevention policy

The experiment service must enforce:

1. Define the prediction unit and split strategy before fitting transformations.
2. Use group-aware splitting for repeated entities, time-aware splitting for temporal prediction, and spatial blocking where spatial dependence applies.
3. Fit imputation, scaling, encoding, feature selection and other learned transformations on training folds only.
4. Keep test labels unavailable to development agents and hyperparameter optimization.
5. Track exact/near duplicates and source overlap across partitions.
6. Record feature availability timestamps and target lineage.
7. Use nested cross-validation when required to estimate model-selection performance.
8. Log every test evaluation and flag repeated test-driven iteration.
9. Run planted leakage tests for target leakage, duplicates, entity overlap, temporal leakage and preprocessing leakage.
10. Block a validated status when a critical check fails or remains unresolved; allow only documented, reviewed exceptions.

No system can prove absolute absence of every possible leakage mode. The product should report the checks performed, their limits, and unresolved risks.

## 7. Evidence ledger

Each manuscript claim should link to one or more evidence records with:
- claim ID and exact claim text;
- source ID, DOI/URL and bibliographic metadata;
- page/section/table/figure or passage locator;
- supporting, contradicting or contextual relationship;
- verification agent and timestamp;
- verification state: verified, partial, disputed or unsupported.

Experiments should use the same lineage model: question → protocol → dataset version → split manifest → code/config → run → metrics/artifacts → reviewed result → manuscript claim.

## 8. Prioritized implementation backlog

### P0 — Stabilize baseline
- Establish a reproducible environment and standard test command.
- Fix and test import paths and runner entry points.
- Replace exact-string LLM routing with typed, validated routing and deterministic fallback.
- Add structured logging, error boundaries and provider configuration validation.
- Create regression tests for all existing behavior.

### P1 — Evidence and retrieval foundations
- Add canonical source records and stable document/chunk IDs.
- Preserve page/section locators and document hashes.
- Implement hybrid retrieval and reranking behind a common interface.
- Add retrieval golden sets and ranking metrics.
- Add claim-to-source evidence records and citation checks.

### P2 — Research workflow
- Add typed task DAG and agent registry.
- Add research planning, screening, gap matrix, critical appraisal and independent review.
- Add human approval gates and task provenance.

### P3 — Data and experiment platform
- Add dataset manifests, immutable versions and schema profiling.
- Add split strategies and transformation pipelines with train-only fitting.
- Add isolated experiment execution and resource limits.
- Add experiment tracking, baselines, statistical analysis and reproducibility checks.

### P4 — Leakage and benchmark assurance
- Add leakage auditor and planted leakage benchmark suite.
- Add algorithm benchmark protocols and regression dashboards.
- Add system-level quality evaluations and release gates.

### P5 — Publication workflow
- Add evidence-grounded manuscript generation.
- Add reference validation, journal style templates and author review.
- Produce manuscript, references, methods appendix and audit/reproducibility pack.

## 9. Definition of done

A capability is complete only when it has:
- typed input/output contracts;
- unit and integration tests;
- failure-path tests;
- documented permissions and data handling;
- observability and provenance;
- evaluation criteria and benchmark results;
- user-facing limitations;
- human approval where scientific judgment or publication is involved.

## 10. Audit limitations and next actions

This is a static first-pass audit based on the public `main` tree and selected source files. No code has been executed, no credentials or private deployment settings have been inspected, and no benchmark performance is claimed.

Next: run baseline tests in a controlled environment, inspect all remaining agent/engine modules, establish a locked dependency environment, and implement P0 on this branch before adding new research capabilities.


## 11. Phase 0 implementation update (2026-11-06)

Changes committed on `researchmind/phase-0-audit` after the initial inspection:

- Hardened `agents/supervisor.py`: validates non-empty requests, normalizes harmless case/whitespace variations in the route label, and raises an explicit error for unsupported router output.
- Tightened the routing prompt with specialist definitions and an instruction to treat the user request as data.
- Added `langchain-openai` and `sentence-transformers` to `requirements.txt`, because the inspected runtime modules import these packages but the previous dependency list did not declare them.
- Added `tests/test_supervisor.py` with unit coverage for Literature, Methodology, Writing, malformed routes and empty input.

**Still open:** `run_researchmind.py` imports an autonomous engine module that is absent from the inspected branch tree (`engine/autonomous_project_engine.py` and `core/autonomous_project_engine.py` were both not found). This is a confirmed static integration blocker; implementing a replacement engine requires reviewing the runner's full task contract and should not be papered over with a stub.

**Validation status:** the GitHub commits succeeded, but tests have not been executed in a local project environment. Do not interpret the added tests as a passing test run. The autonomous runner remains unverified.


## 12. Autonomous engine recovery (2026-11-06)

Added `engine/autonomous_project_engine.py` and the `engine` package to satisfy
the import contract used by `run_researchmind.py`. The engine accepts
`run(query, max_tasks, resume)`, uses the existing `TaskMemory` checkpoint
API, writes task state before and after execution, and returns the
`executed_tasks` structure consumed by the runner.

### Capability boundary

The repository contains three callable specialist agents. The engine maps
these to the first three task IDs:

- `P1-T1`: evidence-grounded literature review (uses the existing local
  vector retriever; it does not perform a live scholarly-web search).
- `P1-T2`: initial methodology proposal.
- `P1-T3`: scholarly writing draft.

The runner declares 26 IDs but supplies no task titles, dependency graph,
acceptance criteria, or handler mapping for the remaining 23. Those records
are explicitly returned as `not_implemented`; they are not presented as
completed research. The three existing agents also have the limitations of
their current implementations and should not be mistaken for validated
doctoral-grade research automation.

### Resume and failure behavior

- Completed tasks are preserved when resuming.
- `max_tasks` limits newly attempted implemented tasks.
- Empty agent output is treated as an error.
- Retryable/quota-like failures are returned to `pending`; other exceptions
  are recorded as `failed`.
- Checkpoints are saved before and after each task.

### Validation status

Added `tests/test_autonomous_project_engine.py` for the runner contract,
task limit behavior, resume preservation, and empty-query validation.
These tests have been authored but **have not been executed** in this
GitHub-only workflow. No runtime, integration, provider, or end-to-end
research validation is claimed.

# Research Assets: Product Specification and UI Architecture

Status: Proposed  
Audience: Product, design, frontend, backend, research operations  
Scope: Information architecture and system design only; no implementation is included

## 1. Executive summary

GEO Engine should introduce **Research Assets** as the home for reusable resources that power research workflows. It should not become a second Settings page or a container for run history.

The product should distinguish three layers:

1. **Catalog definitions** describe what the system knows how to use: platforms, providers, models, and capabilities.
2. **Research assets** are reusable resources owned or configured by the user: platform accounts, connections, browser sessions, datasets, prompts, metrics, and campaigns.
3. **Workflow records** are executions and outputs: generated content, publishing jobs, citation test runs, experiment runs, benchmark executions, and history events.

This separation makes account identity explicit, allows multiple accounts and sessions per platform, and gives every workflow a stable reference to the exact resources it used.

The recommended left navigation is:

```text
Workspace
  Dashboard
  Website Audit

Research
  Content Generation
  Citation Tests
  Experiment Lab
  Benchmarks

Operations
  Publishing Queue
  Content History

Research Assets
  Asset Overview
  Platform Accounts
  Providers & Models
  Datasets
  Prompt Library
  Evaluation Metrics
  Campaigns

Administration
  Settings
```

The active Property remains a workspace scope selector above navigation. Properties are managed in Settings because they define tenancy and scope; they are not ordinary research assets.

## 2. Product principles

### 2.1 Reusable inputs are assets; executions are workflows

A benchmark dataset is an asset. A benchmark execution is a workflow record. A prompt template is an asset. A citation test run using that prompt is a workflow record. A platform account is an asset. A publishing job performed through it is an operational record.

### 2.2 Identity, authentication, and execution are separate

- **Platform account**: who or what the external identity is.
- **Connection**: how GEO Engine is authorized to use it.
- **Session**: a concrete browser or token authentication state.
- **Assignment**: where the account may be used and whether it is preferred.
- **Execution**: the job or run that actually used it.

### 2.3 Purpose is capability-based, not platform-specific

Reddit and Xiaohongshu may publish and retrieve. Perplexity, ChatGPT, Claude, and Gemini may generate, evaluate, retrieve citations, or run experiments. The product should use a common capability vocabulary rather than branching into “social accounts” and “LLM integrations.”

### 2.4 Status must be observable, not inferred from file existence

“A profile directory exists” does not mean the session is authenticated. Connection and session health must be determined by diagnostics, with timestamps and actionable results.

### 2.5 Every run must be reproducible

Execution records should identify the account, connection, session snapshot or version, provider/model, prompt version, dataset version, metric version, and campaign used.

### 2.6 Global assets can be assigned to Properties

External identities usually exist independently of a Property. A Reddit account or Perplexity connection may be usable by several Properties. Property assignment should be explicit rather than duplicating accounts per Property.

## 3. Core domain model

### 3.1 PlatformDefinition

Represents an integration type supported by GEO Engine.

Key fields:

- `id`, stable slug such as `reddit`, `xiaohongshu`, `perplexity`, `openai`
- `display_name`, `category` (`social`, `llm_provider`, `search`, `cms`, future categories)
- `auth_methods` (`browser_profile`, `storage_state`, `api_key`, `oauth`)
- `supported_capabilities`
- `integration_status` (`available`, `beta`, `planned`, `disabled`)
- adapter/version metadata and help URL

Relationships:

- Has many ProviderModels where relevant.
- Has many PlatformAccounts.
- Advertises many CapabilityDefinitions.

Placement: catalog backing **Providers & Models** and **Platform Accounts**. Editing built-in definitions belongs to Administration/Settings; viewing availability belongs in Research Assets.

Management: users do not normally create built-in platform definitions. Administrators enable or disable integrations; developers register new adapters.

### 3.2 PlatformAccount

Represents an external identity or logical research connection. The name is intentionally broad enough for Reddit users, Xiaohongshu identities, browser-backed LLM identities, and API-backed provider connections.

Key fields:

- `id`, `platform_definition_id`
- `username` or provider account identifier
- `display_name`
- `account_type` (`human_identity`, `service_account`, `api_connection`, `anonymous_session`)
- `status` (`active`, `disabled`, `archived`)
- `external_account_id`, when available
- `notes`, tags, ownership/team metadata
- `created_at`, `updated_at`, `last_used_at`

Relationships:

- Has many AccountPurposes.
- Has many AccountCapabilities.
- Has many Connections.
- Has many PropertyAssignments.
- Is referenced by publishing jobs, retrieval tasks, citation tests, experiments, and benchmark executions.

Placement: **Research Assets → Platform Accounts**.

Management: create through “Add account,” choose a platform, name the identity, choose purposes, then configure at least one connection. Edit identity and assignment without modifying its authentication material. Archive instead of deleting when runs reference it.

### 3.3 Connection

Represents one authentication mechanism available to a PlatformAccount.

Key fields:

- `id`, `platform_account_id`
- `connection_type` (`browser_profile`, `storage_state`, `api_key`, `oauth`)
- `label`, such as “Creator Chrome profile” or “Research API key”
- `status` (`connected`, `action_required`, `disconnected`, `disabled`, `error`)
- secret reference, never the secret value in normal API responses
- `local_agent_id` or runtime affinity for local-only credentials
- `last_connected_at`, `last_validated_at`, `last_used_at`
- diagnostic summary and error code

Relationships:

- Belongs to one PlatformAccount.
- Has zero or many BrowserSessions.
- Can expose a subset of account capabilities.
- May be selected by resource assignments and execution records.

Placement: managed inside **Platform Accounts**; API credential policy and secret-store configuration belong in Settings.

Management: add, rename, test, disable, reconnect, or rotate. Destructive deletion is blocked when it is the only healthy connection for active assignments.

### 3.4 BrowserSession

Represents a specific persisted browser authentication state, separate from the account identity.

Key fields:

- `id`, `connection_id`
- `purpose` (`publishing`, `retrieval`, `evaluation`, or custom)
- `profile_path`
- `storage_state_path`
- `storage_format` (`persistent_profile`, `storage_state`, `hybrid`)
- `runtime_location` and `agent_id`
- `browser`, `browser_version`, optional user-agent metadata
- `health_status`
- `last_login_at`, `last_refreshed_at`, `last_validated_at`, `last_used_at`
- `expires_at`, when known
- validation result, failure code, and sanitized evidence
- `is_default` within an account/purpose assignment

Relationships:

- Belongs to one Connection and therefore one PlatformAccount.
- May support multiple capabilities if the platform uses the same authenticated identity.
- Is referenced by immutable execution metadata, ideally as a session ID plus validation/version timestamp rather than copied paths.

Placement: **Research Assets → Platform Accounts**, in account detail and a Sessions tab. Advanced path conventions and local-agent roots belong in Settings.

Management: create via guided login, validate, refresh, set default, move to another registered runtime, or revoke. Paths are system fields, not primary user identifiers.

### 3.5 AccountPurpose and AccountCapability

Purposes explain intended use; capabilities describe verified system actions.

Recommended purpose vocabulary:

- Publishing
- Retrieval
- Evaluation
- Generation
- Experimentation
- Benchmarking

Recommended capability vocabulary:

- `publish_content`
- `retrieve_content`
- `generate_text`
- `run_citation_test`
- `run_experiment`
- `run_benchmark`
- `extract_citations`
- `human_review`

Purpose is user-selected and many-to-many. Capability is derived from the integration, connection type, account permissions, and diagnostics. A user may intend an account for Evaluation, but `run_citation_test` should remain unavailable until its connection passes validation.

### 3.6 PropertyAssignment

Associates a reusable account or asset with one or more Properties.

Key fields:

- `property_id`, `asset_type`, `asset_id`
- allowed purposes/capabilities
- `priority`
- `is_default`
- optional environment or agent constraint
- active date range

This replaces embedding `property_id` directly into every account identity. A single account can be shared deliberately, while defaults remain property-specific.

### 3.7 ProviderModel

Represents an executable model exposed by an LLM platform definition.

Key fields:

- `id`, `platform_definition_id`
- provider model identifier and display name
- modalities and context limits
- supported capabilities
- availability status
- defaults for temperature/token limits where applicable
- deprecation and replacement metadata

Relationships:

- Uses one or more compatible account connections.
- Is selected by prompt templates, experiments, citation tests, and benchmarks.

Placement: **Research Assets → Providers & Models**.

Management: platform adapters synchronize known models; users enable models, set aliases/defaults, and choose which Properties may use them. Provider secrets are configured through a PlatformAccount connection.

### 3.8 Dataset and DatasetVersion

Represents a reusable collection of prompts, queries, examples, expected outputs, or metadata.

Key fields:

- Dataset: name, description, owner, scope, tags, schema, status.
- DatasetVersion: immutable version, source/import metadata, row count, checksum, created timestamp.
- DatasetItem: stable item key, input/query, expected value, metadata, rank/order, split.

Relationships:

- Assigned to Properties or global.
- Used by benchmarks, experiments, citation tests, and prompt-variable previews.
- Dataset versions are referenced by runs for reproducibility.

Placement: **Research Assets → Datasets**.

Management: create manually, import CSV/JSON, duplicate, validate schema, preview rows, version changes, archive. Published versions are immutable.

### 3.9 PromptTemplate and PromptVersion

Represents reusable, versioned instructions rather than prompts embedded in service code.

Key fields:

- PromptTemplate: name, purpose, description, variables/schema, tags, status.
- PromptVersion: system content, user content, provider overrides, model constraints, changelog, version number.

Relationships:

- May be restricted to capabilities or provider models.
- Used by content generation, FAQ generation, citation tests, experiments, and benchmarks.
- References may include a default dataset or metric suite.

Placement: **Research Assets → Prompt Library**.

Management: create, edit drafts, preview with variables, test against an account/model, publish an immutable version, compare versions, deprecate.

### 3.10 EvaluationMetric and MetricVersion

Represents a reusable scoring definition.

Key fields:

- name, description, output type, direction (`higher_is_better`)
- implementation type (`deterministic`, `regex`, `model_judge`, `human_rating`)
- configuration/schema, thresholds, aggregation method
- version and status

Relationships:

- Used by benchmarks, experiments, and citation tests.
- A model-judge metric may depend on a ProviderModel and PromptVersion.

Placement: **Research Assets → Evaluation Metrics**.

Management: create a draft, configure/test it on sample outputs, publish a version, clone, deprecate. Built-in metrics are read-only but clonable.

### 3.11 Campaign

Represents a durable research objective grouping coordinated workflows and assets. The current generic Campaign and ExperimentCampaign should converge conceptually.

Key fields:

- name, objective/hypothesis, status, owner
- Property assignments
- start/end dates
- default providers/models, datasets, prompts, metrics, and accounts
- tags and notes

Relationships:

- Groups content, citation tests, experiments, benchmark runs, and publishing jobs.
- Holds defaults but does not own immutable copies of assets.

Placement: **Research Assets → Campaigns** because campaigns are reusable organizational context. Live campaign execution and results appear in the relevant workflow pages.

Management: create from scratch or template, attach assets, set defaults, launch workflows, archive. The campaign detail page summarizes activity but links to source workflow records.

## 4. Resource placement matrix

| Resource | Purpose | Main relationships | Placement | Management model |
|---|---|---|---|---|
| Properties | Define brand/domain workspace and data scope | Own or scope runs; receive asset assignments | Settings + persistent workspace selector | Create/edit/archive; switch globally |
| Publishing platforms | Describe supported publishing integrations | Accounts, capabilities, formatters, publishers | Research Assets catalog view; enablement in Settings | System-defined; admin enable/disable |
| Browser sessions | Persist browser authentication state | Connection, account, local agent, executions | Platform Accounts | Login, validate, refresh, revoke, set default |
| LLM providers | Describe generation/evaluation integrations | Models, accounts/connections, prompts, runs | Providers & Models | Connect account, test, enable models |
| Publishing accounts | External identities intended to publish | Sessions, property assignments, publishing jobs | Platform Accounts | Add, connect, assign purpose, select default, archive |
| Retrieval accounts | External identities intended to retrieve | Sessions, property assignments, retrieval tasks | Platform Accounts | Same account flow; purpose is Retrieval |
| Citation Tests | Measure provider visibility/citations | Property, prompt, provider/model, account, results | Research workflow, not an asset | Configure/run/compare/history |
| Experiment Lab | Run controlled strategy experiments | Campaign, dataset, prompts, providers, metrics | Research workflow, not an asset | Configure/run/monitor/compare |
| Content Generation | Produce content artifacts | Property, prompt, provider/model, source evidence | Research workflow, not an asset | Generate/review/save/queue |
| Publishing Queue | Execute prepared publishing work | Content, account, session, platform, property | Operations, not an asset | Assign/reassign/retry/review/filter |
| Benchmark datasets | Reusable evaluation inputs | Versions, items, benchmarks, experiments | Datasets | Import/edit/version/validate/archive |
| Prompt templates | Reusable versioned instructions | Providers/models, datasets, workflows | Prompt Library | Draft/test/publish/version/deprecate |
| Evaluation metrics | Reusable scoring definitions | Experiments, benchmarks, citation tests | Evaluation Metrics | Configure/test/version/deprecate |
| Experiment campaigns | Group hypotheses, assets, and runs | Properties, accounts, prompts, datasets, runs | Campaigns | Create/attach defaults/launch/archive |
| Additional providers/platforms | Extend integration catalog | Definitions, capabilities, accounts, adapters | Providers & Models or Platform Accounts | Register definition, connect account, diagnose |

## 5. Research Assets navigation and page architecture

### 5.1 Asset Overview

Purpose: answer “Are my research resources ready?” before a run starts.

Page content:

- Health summary: healthy, action required, unavailable.
- Accounts needing login or validation.
- Provider/model availability.
- Recently used assets.
- Dataset/prompt/metric draft counts.
- Defaults by active Property.
- Quick actions: Add account, Refresh session, Import dataset, Create prompt.

This is operationally useful but does not duplicate workflow results.

### 5.2 Platform Accounts list

Default table columns:

| Column | Behavior |
|---|---|
| Account | Display Name, username, optional avatar |
| Platform | Icon and canonical platform name |
| Purpose | One or more chips: Publishing, Retrieval, Evaluation, etc. |
| Connection | Connected, Action Required, Disconnected, Error |
| Session | Healthy, Expiring, Expired, Missing, Unknown, Not Required |
| Capabilities | Compact capability chips; overflow count |
| Property assignment | All Properties, selected Properties, or Unassigned |
| Last used | Relative time with exact timestamp tooltip |
| Default | Indicates defaults for property/purpose |
| Actions | Open, Test, Refresh, Disable |

Required filters:

- Platform
- Purpose
- Capability
- Connection status
- Session health
- Property assignment
- Active/archived

Required saved views:

- Needs attention
- Publishing
- Retrieval
- LLM evaluation
- All accounts

Multiple accounts on the same platform appear as separate rows. There is no singular “active Reddit account” at the global level. Defaults are resolved by Property + capability/purpose, and the selected account is shown explicitly in every workflow.

### 5.3 Account detail

Header:

- Platform icon, Display Name, `@username` or account identifier
- Purpose chips
- Connection and session health badges
- Primary actions: Test connection, Refresh session, Edit, More

Summary facts must include all requested information:

- Platform
- Username
- Display Name
- Purpose
- Connection Status
- Session Status
- Last Login
- Last Used
- Browser Profile Path
- Storage State
- Supported Capabilities

Tabs:

1. **Overview**: identity, assignments, defaults, capabilities, last activity.
2. **Connections & Sessions**: connection methods, browser sessions, paths, runtime location, validation details.
3. **Diagnostics**: test history, step-level results, errors, sanitized evidence.
4. **Usage**: publishing jobs, retrieval tasks, tests, experiments, benchmarks using this account.
5. **Audit Log**: created, edited, refreshed, assigned, disabled, and selected-as-default events.

Paths should be copyable but visually secondary. Users should recognize an account by identity and purpose, not by filesystem path.

### 5.4 Add account wizard

Step 1 — Select platform/provider:

- Search all available integrations.
- Show category and supported capabilities.
- Clearly mark planned or disabled integrations.

Step 2 — Identify account:

- Display Name, username/account identifier, account type.
- Optional Property assignment.

Step 3 — Select purposes:

- Publishing, Retrieval, Evaluation, Generation, Experimentation, Benchmarking.
- Product previews which capabilities should become available.

Step 4 — Choose connection method:

- Browser login/profile, storage state import, API key, OAuth, or anonymous where supported.

Step 5 — Connect:

- Launch guided authentication or save secret reference.
- For browser auth, show runtime/agent where the profile will live.

Step 6 — Validate and assign defaults:

- Run diagnostics.
- Show verified identity and capabilities.
- Optionally set as default for a Property + purpose.

The wizard produces an account even if connection is deferred, but labels it “Setup incomplete.”

### 5.5 Providers & Models

This page combines provider availability with model configuration without confusing providers with credentials.

Provider card/list fields:

- Provider name and integration status
- Healthy account connections / total connections
- Authentication methods
- Available models
- Supported capabilities
- Last successful diagnostic
- Properties using it

Provider detail tabs:

- Overview
- Accounts & Connections
- Models
- Capabilities
- Diagnostics
- Usage

Model controls include enable/disable, alias, default by workflow, and deprecation warnings. “Connected” is never hard-coded solely because an SDK implementation exists.

### 5.6 Datasets

List: name, scope, current version, item count, schema, last used, owner/status. Detail: overview, data preview, versions, validation, usage. Import flow maps columns to required fields and shows validation before save.

### 5.7 Prompt Library

List: name, purpose, current version, compatible providers, variables, status, last used. Editor: system/user sections, variables, provider overrides, live preview, sample run, diff, publish version.

### 5.8 Evaluation Metrics

List: metric name, type, direction, current version, compatible workflows, status. Detail: definition, configuration, test cases, versions, usage.

### 5.9 Campaigns

List: name, Property scope, objective, status, attached assets, active runs, last activity. Detail: hypothesis, defaults, asset bundle, linked workflows, results summary, activity.

## 6. Session health system

### 6.1 Separate connection status from session health

**Connection status** answers whether GEO Engine can attempt to use the account:

- Connected
- Action Required
- Disconnected
- Disabled
- Error

**Session health** answers whether a specific browser authentication state is usable:

- Healthy
- Expiring Soon
- Expired
- Missing
- Invalid Identity
- Locked/In Use
- Runtime Offline
- Unknown/Stale
- Not Required

### 6.2 Health calculation

Health is derived from:

- Session/profile exists and is readable.
- Required local agent/runtime is online.
- Browser launches successfully.
- Expected platform origin loads.
- Authenticated identity can be detected.
- Detected identity matches the PlatformAccount.
- Capability-specific sentinel elements or API calls succeed.
- Session age and known expiry.
- Last successful use and recent failures.

Recommended display rules:

- Green: validation succeeded within policy window and no subsequent auth failure.
- Amber: expiring, validation stale, runtime offline, or degraded capability.
- Red: expired, identity mismatch, missing state, repeated auth failure.
- Gray: never tested or not applicable.

Every status shows “checked N minutes ago” and exposes the underlying diagnostic result.

### 6.3 Validation cadence

- Validate on creation and refresh.
- Validate before assigning as a default.
- Lightweight validation before a job is claimed.
- Record capability failures during executions.
- Schedule background validation only on the runtime that owns the local credential.

## 7. Connection diagnostics

A diagnostic run should be step-based and capability-aware:

1. Runtime reachable.
2. Credential/profile exists and is readable.
3. Browser/API client starts.
4. Platform origin or endpoint is reachable.
5. Authentication is present.
6. External identity is detected and matches.
7. Requested capability is available.
8. Optional non-destructive interaction check succeeds.

Diagnostic result fields:

- overall status and duration
- tested connection/session/account
- runtime and integration version
- per-step status, timing, error code, and remediation
- URL/status code where safe
- screenshot or sanitized DOM excerpt for browser failures
- `tested_at`, `expires_at` for the result

Diagnostics must never expose API keys, cookies, full storage state, or sensitive profile contents.

User actions:

- “Test all capabilities”
- “Test Publish” / “Test Retrieve” / “Test Citation Test”
- Download sanitized diagnostic report
- Copy remediation command only when a UI workflow is unavailable

## 8. One-click session refresh

The primary account action is **Refresh session**.

Workflow:

1. Preflight identifies the owning local runtime and checks whether the profile is locked.
2. The product launches or signals the local agent to open the platform login/verification page using the existing session location.
3. UI displays “Waiting for login” with platform-specific guidance.
4. User authenticates in the browser and clicks “I’m finished” in the app or confirms through the local agent.
5. The system detects the external identity and compares it with the expected account.
6. Capability diagnostics run.
7. Session timestamps and health update.
8. Any queued jobs blocked by this session become eligible, but are not automatically published.

Failure paths:

- Wrong account detected: offer “Try again”; changing account identity requires explicit confirmation.
- Runtime offline: show which local agent is required and how to reconnect it.
- Profile locked: show owning process/agent if known and allow retry.
- Login incomplete: preserve existing session, do not mark it healthy.
- Validation partially succeeds: show per-capability degraded state.

“Refresh” does not delete the old session first. Revoke/delete remains a separate destructive action.

## 9. Provider capability matrix

The matrix is driven by catalog definitions plus verified connection state. It is not a hard-coded marketing table.

| Provider/platform | Publish | Retrieve | Generate | Citation test | Experiment | Benchmark | Auth modes |
|---|---:|---:|---:|---:|---:|---:|---|
| Reddit | Supported | Supported | — | Indirect/source | — | — | Browser profile; future OAuth/API |
| Xiaohongshu Creator | Supported | — | — | Indirect/source | — | — | Browser profile |
| Xiaohongshu Web | — | Supported | — | Indirect/source | — | — | Browser profile |
| ChatGPT/OpenAI | — | Optional future | Supported | Supported | Supported | Supported | API key; future browser/OAuth |
| Perplexity | — | Citation/source extraction | Supported | Supported | Supported | Supported | Browser profile today; future API |
| Claude | — | Optional future | Planned | Planned | Planned | Planned | API key/OAuth when implemented |
| Gemini | — | Optional future | Planned | Planned | Planned | Planned | API key/OAuth when implemented |

Cell states:

- Supported and healthy
- Supported but connection required
- Supported but degraded
- Planned
- Not supported

The account-level matrix overlays the capabilities available to a specific identity. For example, a Xiaohongshu Creator account and Xiaohongshu Web account can share a platform family while exposing different capabilities and sessions.

## 10. Account selection in workflows

Every workflow should resolve resources using the same rule:

1. Explicit account selected for the current run.
2. Campaign default for the capability.
3. Property default for the capability.
4. Only healthy compatible account, if exactly one exists.
5. Otherwise require user selection.

The UI always shows the resolved resource before execution:

```text
Publishing with: Melantha-G · Reddit · Healthy
Session: Reddit publishing profile · validated 8 minutes ago
```

Publishing Queue rows should retain and show the assigned account. Reassignment is allowed before processing, with compatibility and health checks. Retrieval, citation, experiment, and benchmark configurations follow the same pattern.

No workflow should depend on a hidden global “active account.”

## 11. Settings boundary

Settings should contain administrative and workspace configuration:

- Property management and defaults
- Team/user access when added
- Local agent/runtime registration
- Secret storage policy and environment configuration
- Integration enablement and developer settings
- Data retention, export, audit policy
- Default timezone and notification preferences

Research Assets should contain reusable research resources and their health:

- Platform accounts, connections, and sessions
- Providers and models
- Datasets
- Prompt templates
- Evaluation metrics
- Campaigns

Settings answers “How is this workspace/system configured?” Research Assets answers “What reusable resources can this research use?”

## 12. Current implementation comparison

### 12.1 Current strengths to preserve

- The application is consistently Property-scoped.
- Publishing and retrieval jobs already reference `account_id`.
- The Account model already contains early session-health timestamps.
- Browser execution is correctly delegated to local agents.
- Provider execution is routed through a ProviderManager.
- Citation test runs/results and benchmark definitions/executions are already separated.
- Human review publishing behavior is explicit and should remain unchanged.

### 12.2 Current problems

1. **Account is overloaded.** `handle`, persona, lifecycle, health, platform, session path, and agent metadata mix identity, research persona, operations, and authentication.
2. **Sessions are not first-class.** A path and a few timestamps live on Account; multiple sessions and connection methods cannot be represented.
3. **Canonical paths enforce singletons.** Reddit and Perplexity have one canonical profile; Xiaohongshu has one profile per hard-coded purpose. Multiple accounts per platform cannot work safely.
4. **Provider status is disconnected.** `/providers/status` hard-codes ChatGPT as connected, checks Perplexity directory existence, and labels Claude/Gemini as future stubs. It does not verify credentials, identity, models, or capabilities.
5. **Property ownership duplicates identities.** Demo accounts are cloned and renamed by Property rather than assigned as reusable resources.
6. **Purpose is ambiguous.** `persona` is not an execution purpose, while Xiaohongshu purpose is implicit in path resolution.
7. **No resource-level defaults.** Users cannot see or set the account used for a specific Property and capability.
8. **Settings is a placeholder catch-all.** Property editing, provider status, future publishing accounts, and session gaps appear together without a durable information model.
9. **Reproducibility is partial.** Runs store provider strings and account IDs inconsistently, while prompt/dataset/metric versions are often strings or JSON blobs.
10. **Duplicate campaign concepts exist.** `Campaign` and `ExperimentCampaign` overlap without a unified research context.

### 12.3 Problems solved by the proposal

- Users can identify exactly which account and session each workflow will use.
- Creator and Web identities for the same platform are naturally distinct.
- Multiple accounts per platform become safe and visible.
- Browser profiles are attached to accounts instead of inferred from a platform singleton.
- Session expiry, stale validation, wrong identity, and offline runtime are distinguishable.
- API providers and browser-backed providers share one connection/capability model.
- New providers and social platforms add catalog definitions and adapters without creating new settings concepts.
- Datasets, prompts, and metrics become versioned reusable inputs.
- Campaigns can coordinate workflows without duplicating configuration into every run.
- Execution history becomes reproducible and auditable.

## 13. Proposed migration architecture

### 13.1 New or revised persistence entities

Recommended entities:

- `platform_definitions`
- `capability_definitions`
- `platform_capabilities`
- `platform_accounts`
- `account_purposes`
- `account_capabilities`
- `connections`
- `browser_sessions`
- `property_asset_assignments`
- `provider_models`
- `datasets`, `dataset_versions`, `dataset_items`
- `prompt_templates`, `prompt_versions`
- `evaluation_metrics`, `metric_versions`
- unified `campaigns` plus campaign-asset links
- `diagnostic_runs`, `diagnostic_steps`
- `local_agents` or `runtimes`

Execution tables should add nullable foreign keys first:

- `publishing_jobs`: platform account, connection/session, campaign
- `retrieval_tasks`: platform account, connection/session, campaign
- `citation_test_runs/results`: provider model, platform account/connection, prompt version, dataset item, campaign
- `experiments`: provider model, dataset version, prompt version(s), metric versions, campaign
- `benchmark_executions/results`: provider model, connection, dataset version, prompt/metric versions, campaign
- `contents`: provider model, prompt version, campaign

Run records should also retain a compact immutable execution manifest so historical interpretation survives later asset edits.

### 13.2 Data migration phases

**Phase 0 — Inventory and constraints**

- Inventory Accounts, session paths, actual external identities, provider environment credentials, and local agent locations.
- Identify duplicates created per Property.
- Establish stable platform and capability slugs.

**Phase 1 — Add catalog and asset tables**

- Seed platform definitions for Reddit, Xiaohongshu, OpenAI/ChatGPT, Perplexity, Claude, and Gemini.
- Seed capability definitions and model catalog.
- Keep current APIs operational.

**Phase 2 — Migrate accounts and sessions**

- Convert each real external identity into one PlatformAccount.
- Convert `session_path`/`state_identifier` into Connection and BrowserSession records.
- Convert `property_id` into PropertyAssignments.
- Map `persona` to tags/notes only where valuable; do not treat it as purpose.
- Map current publishing/retrieval usage to explicit purposes and capabilities.
- Deduplicate property-cloned demo accounts carefully; preserve referenced IDs through an alias/mapping table or foreign-key backfill.

**Phase 3 — Introduce account-aware workflow selection**

- Add new foreign keys to jobs/runs.
- Backfill from existing `account_id`, `provider`, `platform`, and session conventions.
- Write both old and new references during a compatibility period.
- Add Property + capability defaults.

**Phase 4 — Migrate provider configuration**

- Represent OpenAI credentials and Perplexity browser identity as PlatformAccounts with Connections.
- Replace hard-coded provider status with catalog, connection, model, and diagnostic data.
- Preserve ProviderManager as execution routing, but resolve a configured connection before instantiation.

**Phase 5 — Version research inputs**

- Convert benchmark query JSON into DatasetVersion/DatasetItem records.
- Import service-level prompt templates into PromptTemplate/PromptVersion records.
- Convert metric JSON/configuration into MetricVersion references.
- Preserve original strings/JSON in execution manifests for historical runs.

**Phase 6 — Unify campaigns and retire legacy fields**

- Define migration rules between Campaign and ExperimentCampaign.
- Backfill campaign links.
- Remove legacy account/session/provider fields only after read paths and jobs no longer depend on them.

### 13.3 Browser profile path migration

The path scheme must become account/session-specific, for example conceptually:

```text
sessions/{platform}/{account_id}/{session_id}/profile
```

Xiaohongshu Creator and Web sessions become separate BrowserSession records rather than hard-coded global directories. Existing directories should be registered in place first; physical moves can happen later with explicit validation and rollback. Never infer that two existing paths belong to the same identity without detecting and confirming the logged-in account.

## 14. API architecture direction

Suggested resource-oriented surfaces:

- `/platform-definitions`, `/capabilities`, `/provider-models`
- `/platform-accounts`
- `/platform-accounts/{id}/connections`
- `/connections/{id}/sessions`
- `/connections/{id}/diagnostics`
- `/sessions/{id}/refresh`
- `/property-asset-assignments`
- `/datasets`, `/datasets/{id}/versions`
- `/prompt-templates`, `/prompt-templates/{id}/versions`
- `/evaluation-metrics`, `/evaluation-metrics/{id}/versions`
- `/campaigns`

Workflow APIs accept explicit resource references or a campaign/default-resolution request. Responses return the fully resolved execution manifest before a run begins.

Local-only actions such as opening a browser session should be commands assigned to a registered local agent, with status streamed or polled back to the UI. The cloud backend should not assume it can inspect a local filesystem path.

## 15. Permissions and security

- Never return credential values, cookies, or full storage state through list/detail APIs.
- Store secret references separately from account metadata.
- Restrict session paths and diagnostics to users with operational access.
- Audit account creation, connection changes, refreshes, validation, default assignment, and revocation.
- Use archive/disable for referenced accounts; require stronger confirmation for credential/session deletion.
- Make local runtime ownership explicit so cloud and local state cannot silently diverge.
- Sanitize screenshots and HTML diagnostics where sensitive data may appear.

## 16. Empty, loading, and failure states

Platform Accounts empty state:

> No research accounts yet. Add a platform or provider account to publish, retrieve, generate, or evaluate.

No compatible account in a workflow:

> No healthy account supports this action for the current Property. Add an account, refresh a session, or change the workflow configuration.

Stale health:

> Last validated 14 days ago. Test connection before use.

Local runtime offline:

> This session lives on “Mel’s Mac” and cannot be reached. Start the local agent or choose another connection.

Wrong identity:

> Expected `@research_account`, but the browser is logged in as `@other_account`. Refresh the session using the expected identity.

## 17. Success criteria

The redesign is successful when:

- A user can identify the exact account, purpose, session, and provider used before every run.
- Multiple accounts on the same platform can coexist without profile collisions.
- Xiaohongshu Creator and Web identities are visible and independently healthy.
- Provider availability reflects actual configured, validated capabilities.
- Session refresh is initiated from the UI and ends with identity/capability validation.
- No workflow relies on a hidden global account or platform-wide profile path.
- Historical runs retain enough asset/version references to reproduce or explain results.
- Adding a provider or platform does not require a new bespoke Settings section.
- Datasets, prompts, and metrics can be reused and versioned across experiments and benchmarks.

## 18. Recommended delivery order

1. Platform definitions, capabilities, Platform Accounts list/detail, and real diagnostics.
2. Connections, BrowserSessions, local runtime registration, and refresh workflow.
3. Property assignments/default resolution and explicit account selection in Publishing and Retrieval.
4. Providers & Models using the same account/connection system.
5. Dataset and prompt versioning.
6. Metric versioning and benchmark UI.
7. Campaign unification and complete execution manifests.

This order addresses today’s highest-risk ambiguity—account and session identity—before expanding the research asset library.

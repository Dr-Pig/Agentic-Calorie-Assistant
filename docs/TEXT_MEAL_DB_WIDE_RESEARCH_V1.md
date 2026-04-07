# Text Meal DB Wide Research v1

## Purpose

這份文件是 `Text Meal DB Wide Research v1` 的實作規格與操作說明。它不是 Greenfield DB 設計原則文件，那些已經寫在：

- `docs/DATA_BUILD_PLAN.md`
- `docs/DATA_SOURCE_POLICY.md`

這份文件只負責把 `wide-research-codex` 的 shard-first / subprocess fan-out 方法，落成目前 repo 可直接執行的 `Source Registry` 建置骨架。

`v1` 只做：
- `Source Registry`

`v1` 不做：
- `Base Nutrition` extraction
- `Exact Item` extraction
- `Meal Pattern` extraction

## Why v1 Stops at Source Registry

目前 `v10.4` 主路徑已經穩定到可以明確知道下一個主幹投資是更大的 local grounding，而不是再加 food-by-food 規則。對應到資料建置，最需要先鎖死的是：

- source tier
- provenance
- source_type
- verification / refresh policy

如果這一層先混髒，後面的 `Base Nutrition / Exact Item / Meal Pattern` 都只會放大污染。

## Runtime Model

`v1` 依賴 `wide-research-codex` 的運作模式：

1. 主控 Codex 先做 reconnaissance
2. 產生 shard manifest
3. 為每個 shard 寫 child prompt
4. 先 dry-run 1-2 個 shard
5. dry-run 通過後再放大 fan-out
6. 用 code 做 coverage / validation / aggregation

這裡的 shard 固定是 **source family**，不是：

- 單一食物
- 品牌 item
- 假想角色分工

## Current Environment Note

在這台 Windows desktop app 環境，`2026-03-30` 實測：

- `codex exec --help`
- `codex mcp list`

都回傳 `Access is denied`。

所以目前 repo 內建的產物會同時支援兩種模式：

- 預設規格：`subprocess mode`
- 現況可行：從外部 terminal 跑 subprocess，或在 app 內退回 session fallback

這個限制必須在 run notes 中記錄，不能假裝 fan-out 已在 app 內成功。

## Repo Artifacts

### Templates and schema

- `data_build/wide_research/source_registry_v1.schema.json`
- `data_build/wide_research/source_registry_v1_manifest.template.json`
- `data_build/wide_research/source_registry_child_prompt.template.md`

### Executable helpers

- `data_build/wide_research/source_registry_v1.py`
- `scripts/scaffold_source_registry_run.py`
- `scripts/validate_source_registry_outputs.py`
- `scripts/aggregate_source_registry.py`

## How to Use

### 1. Scaffold a run

```powershell
python scripts/scaffold_source_registry_run.py
```

這會建立：

```text
data_build/runs/source-registry-v1-YYYYMMDD-HHMMSS/
  manifest.json
  notes.json
  prompts/
  child_outputs/
  logs/
  raw/
  cache/
  tmp/
  aggregated/
  smoke_test.ps1
  dry_run.ps1
  run_all.ps1
```

### 2. Run smoke test

先跑 `smoke_test.ps1`。

- 若通過：可在外部 terminal 照 `dry_run.ps1` -> `run_all.ps1` 走 subprocess mode
- 若失敗：在 notes 裡記錄 fallback，改用 session fallback 跑 child prompts，但輸出格式仍必須是 strict JSON

### 3. Validate outputs

```powershell
python scripts/validate_source_registry_outputs.py data_build/runs/<run_id>
```

輸出：
- `aggregated/validation_report.json`

### 4. Aggregate outputs

```powershell
python scripts/aggregate_source_registry.py data_build/runs/<run_id>
```

輸出：
- `aggregated/aggregated_raw.json`
- `aggregated/source_registry_candidates.json`

## Validation Contract

validation 至少要抓這些錯：

- 缺 shard output
- 空檔
- 非 JSON
- schema mismatch
- duplicate `id`
- 同 URL 出現不同 `tier`
- `P2` 汙染 `base_nutrition / exact_item`
- obvious aggregator/social/blog host 被誤升級成 `P0`

這份 validation report 是 `v1` 的正式交付之一，不可省略。

## What Comes Next

`v1` 完成後，下一波才應該開：

- `v2`: Base Nutrition Wide Research
- `v3`: Exact Item Wide Research
- `v4`: Meal Pattern evidence collection

它們都必須以上一波整理出的 `source_registry_candidates.json` 作為 allowed-source gate。

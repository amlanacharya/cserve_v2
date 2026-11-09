# Spec: development-set benchmark (500 tickets) on a cheap provider

## Problem Statement
The submitted results rest on one 80-ticket validation set. One ticket moves FCR by 1.25 points, a quarter of the set fell back offline because the free Groq tier throttled, and the retrieval-similarity floor was chosen after seeing validation results. The report's own next-step list says the floor and confidence gate should be fitted on the 500 development tickets and the final configuration measured without rate-limit contamination. The free tier cannot process 500 tickets (200k tokens/day).

## Solution
Add OpenRouter as an OpenAI-compatible provider tier. Choose the model with a small, cost-capped bake-off on 20 development tickets. Run all 500 development tickets through the real pipeline with a hard spend cap. Report the result as a development-set benchmark, separate from the validation headline, then (one time, disclosed) rerun the 80 validation tickets on the same provider so the headline is not rate-limit contaminated.

## User Stories
1. As the submitter, I want the pipeline to run 500 tickets without provider throttling, so that the benchmark measures the design and not the free-tier quota.
2. As the submitter, I want the cheapest adequate model chosen on evidence, so that my credit balance is not spent on a larger model than needed.
3. As the submitter, I want a hard spend cap that aborts a run, so that a bug or retry storm cannot drain the account.
4. As a reviewer, I want development-set results kept apart from validation results, so that I can tell tuned figures from held-out ones.
5. As a reviewer, I want every run recorded in the run register with model id, date, spend and fallback count, so that results are reproducible.
6. As the submitter, I want the classification cache to be model-aware, so that a bake-off or a model switch does not silently reuse another model's answers.

## Implementation Decisions
- Provider tier "openrouter" is already added to the cascade, type list and config; `PRIMARY_PROVIDER=openrouter` puts it first. The model is `OPENROUTER_MODEL`.
- Classification cache location comes from `CLASSIFICATION_CACHE_PATH`; the value `none` disables the disk file. Runs on a new model use a new cache file. The existing cache file is left untouched.
- The bake-off is a standalone script that classifies the same 20 stratified development tickets with each candidate model and records intent accuracy, mean stated confidence, parse failures, tokens and cost. Candidates: `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `google/gemini-2.5-flash-lite`, `qwen/qwen3.7-flash`. The Jev router is excluded from the cost-capped run because its price is variable; it may be tried on 5 tickets last.
- Spend guard: before and after each call batch the script reads the key's usage from the provider and aborts if run spend exceeds the cap (bake-off $0.50, dev-500 run $3.00, validation rerun $1.00).
- Model choice rule: the cheapest candidate whose accuracy is within 2 tickets of the best.
- The dev-500 run reuses the existing harness unchanged, with `--delay` small and a separate output file and database.
- Metrics for dev-500 come from the existing metrics module against the dev labels. Because the floor, veto and prompts were designed on dev data, dev results are reported as in-sample for the tuned parts. The report says so.

## Testing Decisions
Behaviour only. Tests: the cache path override is honoured and `none` writes no file; the provider cascade tries OpenRouter first when configured and falls through when it fails (mocked); no test calls a live provider. Existing 136 tests must pass.

## Out of Scope
Training a classifier; HyperFrames film changes beyond updating numbers; voice cloning and the webcam video; changing thresholds based on the dev run (that would be a new tuning round and needs separate disclosure).

## Further Notes
The OpenRouter key sits in `.env` (name `OPENROUTER`) and must never be packaged; the packager asserts this. The key reports about $50 of limit remaining, higher than the $10 the submitter expects; spend caps are set in dollars of usage, not of balance.

# Tickets
1. **Cache path override.** Blocked by: none. Delivers `CLASSIFICATION_CACHE_PATH`, with a test. Done when the cache honours it and 136+ tests pass.
2. **Bake-off.** Blocked by: 1. Script, 20-ticket result file, chosen model in the run register. Done when it ran under the $0.50 cap.
3. **Dev-500 run.** Blocked by: 2. Report JSON, metrics CSV, spend and fallback count. Done when 500 of 500 logged and spend under $3.
4. **Validation rerun on the same provider.** Blocked by: 2. Replaces the headline only if fallbacks are near zero; otherwise the old run stays and this is listed as run 5.
5. **Deliverables refresh.** Blocked by: 3, 4. Report section 7 and Table 3, README, video script and film numbers, effort log entry, rebuilt PDF and zip.

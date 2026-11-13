# Frozen run configuration (development-set benchmark, 8 November 2026)

| Item | Value |
|---|---|
| Input | `05_Datasets/development_tickets.json` (500 tickets, labelled) |
| Code | commit recorded at the time of the run (see git log) |
| Providers | OpenRouter, Groq, Gemini, round-robin, failover on error |
| Models | OpenRouter and Groq `openai/gpt-oss-20b`; Gemini `gemini-3.1-flash-lite` |
| Thresholds | confidence 0.75, similarity floor 0.40, top-k 3 |
| Prompts | classification v1; generation v2 (`prompts/`) |
| Cache | `data/cache/dev500_cache.json`, keys fingerprinted by provider order, strategy and models |
| Spend cap | `MAX_SPEND_USD=2`, checked every 20 OpenRouter calls |
| Bake-off | `evaluation/experiments/model_bakeoff_results.json`: 20 stratified dev tickets, 4 candidate models, total spend under $0.01 |

Reading these results: the similarity floor, intent veto, generation prompt and stemmed guard were all tuned on development
and validation data, so the figures are **in-sample for the tuned components** and are not a generalisation estimate. They show
that the design runs unattended on 500 tickets without provider throttling. The hidden set remains unused.

## Ablation: similarity floor 0.30 (11 November 2026)

Same economy configuration and cached classifications as above, with `RETRIEVAL_SIMILARITY_FLOOR=0.3`.
Outputs: `dev500_floor0.3.json`, `dev500_floor03_decisions.db`, `val_floor0.3.json`, `val_floor03_decisions.db`. See report Section 7.8.
The configured default remains 0.40. No 0.40 control re-run was made, so generation variation is not isolated.

## Regenerate-on-failure runs (11 November 2026)

Floor 0.40, `MAX_SPEND_USD=2`, classification caches copied per run from `val_run5_cache.json` / `dev500_cache.json`. `GUARDRAIL_RETRY=1` or `GUARDRAIL_RETRY_STRICT=1` as named; "120b" = `PROVIDER_ORDER=openrouter`, `OPENROUTER_MODEL=openai/gpt-oss-120b`. Dev 500: `dev500_retry`, `dev_strict`, `dev_120b_retry` (plus earlier `dev500`, `dev500_gptoss120b_openrouter`). Val 80: `val_ctrl`, `val_retry`, `val_strict`, `val_120b_retry`, `val_120b_strict`, `val_120b_noretry` (each with `*_decisions.db`). Scored against dataset labels; see report Section 7.9. Defaults unchanged (retry off); recommended safe profile is `gpt-oss-120b` without retry; max-FCR opt-in is 120b + retry (63.4% dev, 5/87 must-not answered).

- val_final_safe / val_final_assisted (13 Nov 2026): validation n=80, OpenRouter gpt-oss-120b, floor 0.40, GUARDRAIL_RETRY off / on. FCR 37.5% (30) / 52.5% (42); 2 of 80 tickets served by Gemini after OpenRouter timeouts. Report Section 7.10.

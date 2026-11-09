"""Cost-capped classification bake-off across cheap OpenRouter models on development tickets.

Calls the classification prompt directly (no cache, no pipeline), so each model sees every ticket.
Spend is read from the provider's key endpoint before and after each model and the run aborts if the
cap is exceeded.

Usage: python -m evaluation.experiments.model_bakeoff [--n 20] [--cap 0.5] [model ...]
"""
import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

os.environ["PROVIDER_ORDER"] = "openrouter"
os.environ["CLASSIFICATION_CACHE_PATH"] = "none"

from src.classify.classifier import extract_json_from_llm_output  # noqa: E402
from src.core.config import get_settings  # noqa: E402
from src.core.types import INTENT_LABELS  # noqa: E402
from src.generation.cascade import call_cascade  # noqa: E402
from src.generation.prompts import CLASSIFICATION_SYSTEM_PROMPT, format_classification_prompt  # noqa: E402

DEFAULT_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "google/gemini-2.5-flash-lite", "qwen/qwen3.7-flash"]
DEV = Path("05_Datasets/development_tickets.json")
OUT = Path("evaluation/experiments/model_bakeoff_results.json")


def usage() -> float:
    s = get_settings()
    r = httpx.get(f"{s.openrouter_base_url}/key", headers={"Authorization": f"Bearer {s.openrouter_api_key}"}, timeout=20)
    r.raise_for_status()
    return float(r.json()["data"]["usage"])


def stratified_sample(tickets: list[dict], n: int, seed: int = 7) -> list[dict]:
    by_intent: dict[str, list[dict]] = defaultdict(list)
    for t in tickets:
        by_intent[t["labels"]["intent"]].append(t)
    rng = random.Random(seed)
    picked: list[dict] = []
    intents = sorted(by_intent)
    while len(picked) < n:
        for i in intents:
            if by_intent[i] and len(picked) < n:
                picked.append(by_intent[i].pop(rng.randrange(len(by_intent[i]))))
    return picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="*", default=DEFAULT_MODELS)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--cap", type=float, default=0.5, help="abort if total spend in USD exceeds this")
    args = ap.parse_args()

    tickets = stratified_sample(json.load(open(DEV, encoding="utf-8")), args.n)
    start_total = usage()
    results = {}
    for model in args.models:
        os.environ["OPENROUTER_MODEL"] = model
        get_settings.cache_clear()
        before = usage()
        correct = parse_fail = 0
        confs: list[float] = []
        lat: list[float] = []
        providers = set()
        for t in tickets:
            t0 = time.time()
            text, provider = call_cascade(
                CLASSIFICATION_SYSTEM_PROMPT, format_classification_prompt(t.get("subject"), t["body"]), 0.0, "classification"
            )
            lat.append(time.time() - t0)
            providers.add(provider)
            try:
                p = extract_json_from_llm_output(text)
                intent = str(p.get("inferred_intent", "")).strip()
                confs.append(float(p.get("confidence", 0)))
                if intent not in INTENT_LABELS:
                    parse_fail += 1
                correct += intent == t["labels"]["intent"]
            except Exception:
                parse_fail += 1
            if usage() - start_total > args.cap:
                print("SPEND CAP EXCEEDED, aborting")
                sys.exit(2)
        spent = usage() - before
        results[model] = {
            "n": len(tickets), "correct": correct, "accuracy": round(correct / len(tickets), 3),
            "parse_or_vocab_failures": parse_fail, "mean_confidence": round(sum(confs) / max(1, len(confs)), 3),
            "mean_latency_s": round(sum(lat) / len(lat), 2), "providers_seen": sorted(providers),
            "spend_usd": round(spent, 5),
        }
        print(model, results[model])
    OUT.write_text(json.dumps({"tickets": [t["ticket_id"] for t in tickets], "results": results}, indent=2), encoding="utf-8")
    print("total spend", round(usage() - start_total, 5))


if __name__ == "__main__":
    main()

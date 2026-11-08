# Routing Component

## Overview
The `routing` package evaluates independent orthogonal gating rules (intent confidence and semantic retrieval similarity) to deterministically determine whether a support inquiry can be automatically answered or must be escalated to human tier-2 engineers.

## Interface
- `[src/routing/router.py:evaluate_route]`: `evaluate_route(confidence: float, top_retrieval_score: float, urgency: Urgency, must_not_auto_respond: bool, tau: float | None = None, sigma: float | None = None, provider_used: Provider | None = None, node_failure: str | None = None) -> tuple[RoutingAction, str]` evaluates gating formulas and produces diagnostic reason strings.
- `[src/routing/escalation.py:build_escalation_packet]`: `build_escalation_packet(ticket_id: str, final_disposition: EscalatedDisposition, routing_reason: str, inferred_intent: str, intent_confidence: float, intent_alternatives: dict[str, float] | None, urgency: Urgency, candidate_docs: list[DocumentChunk], provider_used: Provider, guardrail_violations: list[str] | None = None) -> EscalationPacket` bundles triage context for deflected tickets.

## Invariants
- `[src/routing/router.py:evaluate_route]`: Emits `"AUTO_RESPOND"` if and only if:
  1. Intent confidence $c \ge \tau$ (default 0.75)
  2. Retrieval similarity $s_{\text{ret}} \ge \sigma$ (default 0.65)
  3. Urgency is strictly not `"CRITICAL"`
  4. Safety veto flag `must_not_auto_respond` is `False`
- `[src/routing/router.py:evaluate_route]`: Any active `node_failure` or `provider_used == OFFLINE_PROVIDER` unconditionally forces `"ESCALATE"`.
- `[src/routing/escalation.py:build_escalation_packet]`: Attaches up to `top_k_escalate` (default 2) candidate document chunks to provide human triage context.

## Side Effects
- None: purely deterministic routing math and state creation without external network, disk, or memory mutation.

## Verification
- Run: `pytest tests/unit/test_routing.py -v`


# 0002: Route all LLM calls through a LiteLLM gateway

## Decision
The backend calls a LiteLLM proxy with a scoped virtual key and model aliases
(agent-main, agent-fast). Claude Sonnet is primary; Groq Llama is the fallback.

## Why
- Provider keys stay in the gateway; a leaked backend key is revocable and budget-capped.
- Switching models is a config change, not a code change.
- Retries, fallbacks, budgets, and spend tracking live in one layer.
- Retries happen only in the gateway (SDK max_retries=0) to avoid retry storms.

## Trade-offs
- One more service to run and deploy.
- The gateway is a single point of failure; it needs health checks and restart policies.
# LLM Backend Routing

> How a single model name reaches Gemini OR any OpenAI-compatible API (GLM, DeepSeek, Ollama…).
> Status: **skeleton**. This is the biggest change in this fork (R1.1 — keep in sync).

## The problem it solves

Original code hardcoded Gemini in every agent. This fork adds a routing layer so one
config switch (`LLM_BACKEND`) sends everything to an OpenAI-compatible endpoint.

## Config (`.env`)

```
LLM_BACKEND=openai_compatible        # auto | openai_compatible | gemini
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4
# (Gemini keys only needed if LLM_BACKEND=gemini/auto routes there)
GEMINI_API_KEY=   VERTEX_AI_PROJECT=   VERTEX_AI_LOCATION=
```

## Code pointers

- Routing: `utils/llm_backend_utils.py`
  - `_is_openai_backend(model_name)` — the routing decision
  - `call_llm_with_text_prompt`, `call_llm_with_images`, `call_llm_with_pdf`
  - `parse_latex_results`, `parse_json_latex_response` (generic parsers)
- Clients (lazy-initialized so the unused one never errors):
  - `utils/openai_utils.py::_get_openai_client` — honors `OPENAI_BASE_URL`
  - `utils/gemini_utils.py::_get_genai_client`

## Routing logic

```
LLM_BACKEND=openai_compatible  → ALL models → OpenAI path
LLM_BACKEND=gemini             → ALL models → Gemini path
LLM_BACKEND=auto (default)     → model name has gpt/o1/o3 → OpenAI; else Gemini
```

> ⚠️ In `auto`, `glm-5.3` would wrongly route to Gemini. **Set `LLM_BACKEND=openai_compatible`.**

## Default model

`paper_writing_cli.py` defaults: `--writer_model_name glm-5.3`, `--reflection_model_name glm-5.3`.

## Notes / gotchas

- Temperature is dropped for OpenAI reasoning models (o1/o3) in `call_llm_with_text_prompt`.
- The Zhipu **coding** endpoint (`/api/coding/paas/v4`) has separate quota from the standard one.

## TODO / flesh out

- [ ] Document `call_llm_with_pdf` behavior per backend (raw bytes vs extracted text)
- [ ] Add DeepSeek/Ollama example configs

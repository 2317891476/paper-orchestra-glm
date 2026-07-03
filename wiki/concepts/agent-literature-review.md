# Agent — Literature Review

> Stage 2: find real papers, build `references.bib`, write Introduction + Related Work.
> Status: **skeleton**. This agent has the **venue-targeting** mechanism added in this fork.

## Role

`HybridLiteratureAgent` collects candidate papers for each section, enriches them via
Semantic Scholar (verifying they're real + within cutoff), then synthesizes LaTeX for
the Introduction and Related Work sections.

## Code pointers

- Agent: `methods/agents/literature_review_agent.py` — `HybridLiteratureAgent`
- Prompt: `methods/prompts/literature_review_agent.py` — `literature_review_agent_writter_prompt`
- Search: `utils/scholar_utils.py` — `s2_title_search` (Semantic Scholar, no key needed)

## Venue targeting (this fork's key addition)

- `_load_target_venues(guidelines_path)` reads `venues.md` from the template dir
  (same folder as `guidelines.md`).
- The venue list is injected into `_discover_candidates` prompts so the LLM prefers
  the target community's papers (HPCA → ISCA/MICRO/HPCA/ASPLOS/DAC…).
- To retarget: edit `templates/<conf>/venues.md`. See [latex-templates](latex-templates.md).

## Phases

1. **Discovery** — `_discover_candidates` (per search task, parallel). Now uses **multi-source
   search** (`search_papers`: DeepXiv+S2+arXiv) merged with LLM-knowledge candidates — see
   [paper-search](paper-search.md). Finds real papers even when S2 is rate-limited.
2. **Retrieval** — `s2_title_search` enrichment, rate-limited (~1 req/s)
3. **1.5 Local references** — `_load_and_register_local_references` ingests user-provided
   PDF/.bib into the registry (bypasses S2 + cutoff). See [local-references](local-references.md).
4. **Writing** — synthesize intro + related work LaTeX (appends the style guide, if any,
   to the writer system prompt; see [agent-style](agent-style.md))

## Outputs

- `updated_template.tex`, `references.bib`, `citation_map.json`, `outline_v1.json`

## Notes / gotchas

- Without a Gemini key, Google Search is unavailable; the agent falls back to LLM
  knowledge for candidates, then verifies existence via Semantic Scholar.
- `Semantic Scholar` works keyless but rate-limited (~100/5min); set
  `SEMANTIC_SCHOLAR_API_KEY` for higher limits.

## TODO / flesh out

- [ ] Document the search-task collection logic (`_collect_search_tasks`)
- [ ] Cutoff-date semantics in `_is_paper_allowed`

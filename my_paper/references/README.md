# references/ — local, always-citable references (optional)

Drop papers you know are highly relevant here. They bypass the Semantic Scholar search and
the cutoff-date filter — they are **guaranteed citable**, and the writers are nudged to prefer them.

Accepted formats (mix freely):
- `*.bib` — parsed by a lightweight regex parser; map title/authors/year/venue/abstract.
- `*.pdf` — text extracted, then one LLM call pulls {title, authors, year, venue, abstract}.

Example `.bib` entry:
```bibtex
@inproceedings{Smith2024Foo,
  title   = {The Foo Architecture: A New Approach},
  author  = {John Smith and Jane Doe},
  booktitle = {Proceedings of HPCA},
  year    = {2024},
  abstract = {We propose Foo, a novel architecture that improves throughput by 30%.}
}
```

These get merged into the literature agent's pool → `references.bib` + `citation_map.json`
(marked `is_local: true`). Leave this folder empty (or just this README) to skip the feature.

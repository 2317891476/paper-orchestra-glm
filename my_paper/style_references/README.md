# style_references/ — target-conference "best papers" for style learning (optional)

Drop 1–3 representative PDFs from your target venue here. The StyleAgent (pipeline step 1.5)
reads them and distills a writing-style profile (voice, section structure, citation habits,
sentence-level phrasing templates) that the literature + section writers mimic.

- Priority: this folder (run-level) > `templates/<conf>/style_papers/` (conference-level).
- Cap: 3 papers (visual extraction is token-heavy).
- Filenames deduped by basename.
- Leave empty to skip style learning (writers use a generic academic voice).

Example: for an HPCA submission, drop 2–3 strong recent HPCA/ISCA/MICRO papers in your sub-area.

# figures/

Drop your figure files here (`.png` / `.jpg` / `.pdf`). They get copied into the LaTeX build.

## info.json — figure manifest (optional but recommended)

`info.json` tells the Section agent which figures exist and their captions. Schema:

```json
[
  {
    "name": "architecture.png",
    "caption": "Overview of <SystemName>. Left: ... Right: ..."
  },
  {
    "name": "results.png",
    "caption": "Main results comparing Ours vs baselines on metric A."
  }
]
```

Rules:
- `name` must match a file in this folder (extension included).
- `.png` / `.jpg` are passed to the vision model (it "sees" them and writes faithful descriptions).
- `.pdf` figures compile fine but the model can't view them — provide a `.png` preview too if you want it described accurately.
- Leave `info.json` as `[]` if you have no figures (the pipeline still runs; the Section agent just writes text + tables).

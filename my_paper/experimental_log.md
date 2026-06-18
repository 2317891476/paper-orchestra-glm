# Experimental Log — <Your Paper Title>

<!--
  This is a TEMPLATE for `experimental_log.md` — the data source for tables/results.
  The Section agent reads this and BUILDS LaTeX tables directly from the numbers here
  (booktabs). It will NOT invent numbers — so write them all out, accurately.

  Use Markdown tables. The agent transcribes them into \begin{table}...\end{table}.
-->

## 1. Evaluation Setup
<!--
  Datasets/benchmarks, splits, metrics, hardware, hyperparameters.
-->
- **Datasets**: ...
- **Metrics**: ...
- **Baselines**: ...
- **Hardware**: ...
- **Hyperparameters**: ...

## 2. Main Results

**Table 1: <what this table shows>**

| Method | Metric A | Metric B | Metric C |
| :--- | :---: | :---: | :---: |
| Baseline 1 | 00.0 | 0.00 | 0.0 |
| Baseline 2 | 00.0 | 0.00 | 0.0 |
| **Ours** | **00.0** | **0.00** | **0.0** |

## 3. Ablation Study

**Table 2: Ablation on <component>**

| Setting | Metric A | Metric B |
| :--- | :---: | :---: |
| Full method | **00.0** | **0.00** |
| - component X | 00.0 | 0.00 |
| - component Y | 00.0 | 0.00 |

## 4. Qualitative Observations
<!--
  Prose analysis: what works, what doesn't, why. The Section agent weaves this into
  the Experiments discussion. Concrete > vague.
-->
- **Observation 1**: ...
- **Observation 2**: ...

## 5. Limitations & Future Work
- ...

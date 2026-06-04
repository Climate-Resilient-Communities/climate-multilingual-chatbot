# Tiny-Aya Regional Translation Bake-off

A head-to-head translation evaluation of Cohere Labs' **Tiny-Aya** regional
models, modeled on the original `combined_bake_off.py`. Each model is tested on
the languages it is actually routed to in production
(`src/models/cohere_flow.py`).

## Models

| Region | Model id (Cohere API) | Tested languages |
|--------|-----------------------|------------------|
| Global | `tiny-aya-global` | all 18 in the dataset (generalist baseline) |
| Fire   | `tiny-aya-fire`   | Hindi, Urdu, Gujarati, Tamil, Bengali (South Asian) |
| Water  | `tiny-aya-water`  | Arabic, Chinese, Russian, Japanese, German, French, Spanish, Filipino, Portuguese, Persian, Korean, Italian, Vietnamese |
| Earth  | `tiny-aya-earth`  | **skipped by default** — see note |

> **Earth is skipped.** The reference dataset (`translated_OPENAI.csv`) contains
> no African languages, so the Earth model cannot be scored against it. To
> include it, add African reference translation columns (e.g. `sw_translated_OPENAI`)
> to the CSV and run with `--models global fire water earth`.

## How to run

This must run somewhere that can reach `api.cohere.com` (the Claude Code web
sandbox blocks it via its network allowlist). From the repo root:

```bash
pip install -r "Multilingual testing/requirements-bakeoff.txt"

export COHERE_API_KEY="your-cohere-key"
python "Multilingual testing/tiny_aya_bakeoff.py"
```

### Options

```bash
# Pick which regional models to run
python "Multilingual testing/tiny_aya_bakeoff.py" --models global fire water

# Limit the number of source phrases (default: all 8)
python "Multilingual testing/tiny_aya_bakeoff.py" --num-phrases 4

# Offline pipeline check — no API calls, stand-in translations
python "Multilingual testing/tiny_aya_bakeoff.py" --dry-run
```

## What it does

1. Loads English source phrases + OpenAI reference translations from
   `translated_OPENAI.csv`.
2. For each model, translates every phrase into its routed languages using the
   **exact production prompt** from `CohereModel.translate()`.
3. Scores each translation with **BLEU + chrF** via `sacrebleu` (no HuggingFace
   dependency — the original used `evaluate.load(...)`, which downloads from the
   HF hub and fails behind a restricted network).
4. Caches translations in `tiny_aya_cache.json` so re-runs are cheap.
5. Writes outputs to `reports/`:
   - `tiny_aya_results.csv` — every translation + scores
   - `tiny_aya_bakeoff_report.md` — rankings + per-language detail
   - `tiny_aya_chrf_heatmap.png` — if matplotlib/seaborn are installed

## Scoring

Overall score = Translation Quality (70%) + Response Speed (30%). Cost is
omitted because Tiny-Aya pricing is not published; per-translation latency is
recorded instead.

## Differences from the original bake-off

- Models: 3 Tiny-Aya regional models instead of the 9 Bedrock/Cohere models.
- Languages are **matched per model** to production routing, not all-vs-all.
- Metrics via `sacrebleu` instead of HuggingFace `evaluate` (network-free).
- Translation prompt mirrors current production `cohere_flow.py`.

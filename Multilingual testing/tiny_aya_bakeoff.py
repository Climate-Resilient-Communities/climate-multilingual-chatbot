"""
Tiny-Aya Regional Translation Bake-off
======================================

Head-to-head translation evaluation of Cohere Labs' Tiny-Aya regional models,
each tested on the languages it is actually routed to in production
(see src/models/cohere_flow.py).

Models (via the Cohere API):
    - Tiny-Aya Global  (tiny-aya-global) — generalist / fallback, all languages
    - Tiny-Aya Fire    (tiny-aya-fire)   — South Asian languages
    - Tiny-Aya Water   (tiny-aya-water)  — Asia-Pacific + W. Asia + Europe
    - Tiny-Aya Earth   (tiny-aya-earth)  — African languages  [SKIPPED: see note]

NOTE on Earth: the reference dataset (translated_OPENAI.csv) contains no African
languages, so the Earth model cannot be scored against it. It is excluded by
default. Add African reference translations and pass `--models earth` to include it.

Scoring mirrors the original bake-off: BLEU + chrF against OpenAI reference
translations. Unlike the original, metrics use `sacrebleu` (pip-installable, no
network) instead of HuggingFace `evaluate`, and translation uses the exact
production prompt from CohereModel.translate().

Usage:
    COHERE_API_KEY=... python "Multilingual testing/tiny_aya_bakeoff.py"
    COHERE_API_KEY=... python "Multilingual testing/tiny_aya_bakeoff.py" --models global fire water
    python "Multilingual testing/tiny_aya_bakeoff.py" --dry-run      # offline pipeline check

Outputs land in `Multilingual testing/reports/`:
    - tiny_aya_results.csv
    - tiny_aya_bakeoff_report.md
    - (optional charts if matplotlib/seaborn are installed)
"""
import argparse
import json
import os
import random
import time
from datetime import datetime

import pandas as pd
import sacrebleu

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- Paths (resolved relative to this script, so cwd doesn't matter) ---------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_CSV = os.path.join(SCRIPT_DIR, "translated_OPENAI.csv")
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")
CACHE_FILE = os.path.join(SCRIPT_DIR, "tiny_aya_cache.json")

# --- Models under test ------------------------------------------------------
# Cohere API model ids — identical to production (src/models/cohere_flow.py).
TINY_AYA_MODELS = {
    "global": ("Tiny-Aya Global", "tiny-aya-global"),
    "fire":   ("Tiny-Aya Fire",   "tiny-aya-fire"),
    "water":  ("Tiny-Aya Water",  "tiny-aya-water"),
    "earth":  ("Tiny-Aya Earth",  "tiny-aya-earth"),
}

# --- Regional language routing ----------------------------------------------
# Canonical source: src/models/cohere_flow.py (FIRE/EARTH/WATER_LANGUAGES).
# Mirrored here so the bake-off runs standalone. Keep in sync with production.
FIRE_LANGUAGES = frozenset({
    'hi', 'bn', 'pa', 'ur', 'gu', 'ta', 'te', 'mr',
    'ne', 'si', 'ml', 'kn', 'or', 'as', 'sd', 'ks',
})
EARTH_LANGUAGES = frozenset({
    'sw', 'yo', 'ha', 'ig', 'am', 'so', 'rw', 'sn', 'zu', 'xh',
    'st', 'tn', 'ny', 'lg', 'wo', 'ff', 'bm', 'ti', 'om', 'rn',
})
WATER_LANGUAGES = frozenset({
    'zh', 'ja', 'ko', 'th', 'vi', 'id', 'ms', 'tl', 'my', 'km',
    'lo', 'mn', 'ka', 'jv',
    'ar', 'he', 'fa', 'tr', 'ku',
    'ru', 'uk', 'pl', 'cs', 'ro', 'el', 'bg', 'sr', 'hr', 'sk',
    'sl', 'hu', 'lt', 'lv', 'et', 'nl', 'de', 'fr', 'it', 'pt',
    'es', 'sv', 'da', 'no', 'fi', 'is', 'ca', 'gl', 'eu', 'sq',
    'bs', 'mk', 'mt',
})

REGION_LANGUAGE_SETS = {
    "fire": FIRE_LANGUAGES,
    "earth": EARTH_LANGUAGES,
    "water": WATER_LANGUAGES,
    # "global" matches every language in the dataset (handled specially below).
}

# Human-readable names for the languages present in the reference dataset.
LANGUAGE_NAMES = {
    "ar": "Arabic", "zh": "Chinese", "ru": "Russian", "ja": "Japanese",
    "hi": "Hindi", "de": "German", "fr": "French", "es": "Spanish",
    "tl": "Filipino (Tagalog)", "pt": "Portuguese", "fa": "Persian",
    "ur": "Urdu", "ko": "Korean", "it": "Italian", "ta": "Tamil",
    "bn": "Bengali", "vi": "Vietnamese", "gu": "Gujarati",
}

# sacrebleu tokenizers for languages that need script-aware segmentation.
BLEU_TOKENIZERS = {"zh": "zh", "ja": "ja-mecab", "ko": "ko-mecab"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_reference_data(num_phrases=None, seed=42):
    """Load source phrases and per-language OpenAI reference translations."""
    if not os.path.exists(DATA_CSV):
        raise FileNotFoundError(f"Reference data not found: {DATA_CSV}")
    df = pd.read_csv(DATA_CSV)
    df = df[df["en_source_text"].notna()].reset_index(drop=True)

    if num_phrases and num_phrases < len(df):
        random.seed(seed)
        idx = sorted(random.sample(range(len(df)), num_phrases))
        df = df.iloc[idx].reset_index(drop=True)

    phrases = df["en_source_text"].tolist()
    references = {}
    for code in LANGUAGE_NAMES:
        col = f"{code}_translated_OPENAI"
        if col in df.columns:
            references[code] = df[col].tolist()
    return phrases, references


def languages_for_model(region, available_codes):
    """Return the dataset language codes a given regional model should be tested on."""
    available = set(available_codes)
    if region == "global":
        return [c for c in LANGUAGE_NAMES if c in available]
    region_set = REGION_LANGUAGE_SETS.get(region, frozenset())
    return [c for c in LANGUAGE_NAMES if c in available and c in region_set]


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------
def build_prompt(text, target_lang_name):
    """Production translate() prompt, mirrored from src/models/cohere_flow.py."""
    terminology_rules = (
        "When responding in a non-English language, always use professional, "
        "domain-specific climate terminology consistent with authoritative sources "
        "in that language (e.g., IPCC translations, national climate reports). "
        "Avoid over-simplified or generic translations of technical terms; preserve "
        "scientific accuracy while keeping explanations understandable. "
    )
    zh_rules = (
        "If the target language is Chinese, use standard climate-science terms from "
        "the China Meteorological Administration and IPCC: use ‘全球气候变化’ when "
        "referring to the global phenomenon, ‘气候变化缓解’ for mitigation, and "
        "‘极端气候事件’ for extreme events."
    )
    extra = zh_rules if target_lang_name.lower().startswith("chinese") else ""
    return (
        "You are a professional climate-science translator.\n"
        f"Translate the following text from English to {target_lang_name}.\n"
        "Style: Formal. Tone: Informative.\n"
        f"{terminology_rules}{extra}\n"
        "Provide ONLY the translation, with no preface or notes.\n\n"
        "Text:\n" + text + "\n\nTranslation:"
    )


def translate(client, model_id, text, target_lang_name, cache, dry_run=False, max_retries=3):
    """Translate one phrase. Returns (translation, response_time, from_cache)."""
    cache_key = f"{model_id}|{target_lang_name}|{text}"
    if cache_key in cache:
        c = cache[cache_key]
        return c["translation"], c["response_time"], True

    if dry_run:
        # Offline pipeline check: echo a deterministic stand-in.
        time.sleep(0)
        return f"[{target_lang_name}] {text}", 0.0, False

    prompt = build_prompt(text, target_lang_name)
    start = time.time()
    translation = None
    for attempt in range(max_retries):
        try:
            resp = client.chat(model=model_id, message=prompt, temperature=0.1)
            translation = (resp.text or "").strip()
            break
        except Exception as e:
            wait = 2 ** attempt
            print(f"    ...error on {model_id}/{target_lang_name}: {e}. retrying in {wait}s")
            time.sleep(wait)
    if not translation:
        return None, 0.0, False

    response_time = time.time() - start
    cache[cache_key] = {"translation": translation, "response_time": response_time}
    return translation, response_time, False


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score(hypothesis, reference, lang_code):
    """Return (bleu_0_1, chrf_0_100) for a single sentence pair."""
    tok = BLEU_TOKENIZERS.get(lang_code)
    try:
        if tok:
            bleu = sacrebleu.sentence_bleu(hypothesis, [reference], tokenize=tok).score
        else:
            bleu = sacrebleu.sentence_bleu(hypothesis, [reference]).score
    except Exception:
        bleu = sacrebleu.sentence_bleu(hypothesis, [reference]).score
    chrf = sacrebleu.sentence_chrf(hypothesis, [reference]).score
    return bleu / 100.0, chrf


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def generate_report(results_df, timestamp, tested):
    if results_df.empty:
        return "No results were generated."

    scores = results_df.groupby("Model").agg(
        BLEU=("BLEU", "mean"),
        chrF=("chrF", "mean"),
        Response_Time=("Response_Time_Seconds", "mean"),
    )
    scores["Quality_Score"] = (scores["BLEU"] + scores["chrF"] / 100) / 2
    scores["Speed_Score"] = 1 / (1 + scores["Response_Time"])
    scores["Overall_Score"] = scores["Quality_Score"] * 0.7 + scores["Speed_Score"] * 0.3
    winner = scores["Overall_Score"].idxmax()

    out = [f"# Tiny-Aya Regional Translation Bake-off Report\n",
           f"**Generated:** {timestamp}\n",
           "## Executive Summary\n",
           (f"Evaluated {results_df['Model'].nunique()} Tiny-Aya regional models on "
            f"{results_df['Language'].nunique()} languages × "
            f"{results_df['Source Text'].nunique()} phrases, each model run on the "
            f"languages it is routed to in production.\n"),
           f"### 🏆 Overall Winner: **{winner}**\n",
           "Weighted score = Translation Quality (70%) + Response Speed (30%). "
           "Cost is omitted (Tiny-Aya pricing not published).\n",
           "## Models & Language Coverage\n"]
    for model_name, langs in tested.items():
        names = ", ".join(LANGUAGE_NAMES[c] for c in langs)
        out.append(f"- **{model_name}** ({len(langs)} langs): {names}")
    out.append("")

    out.append("## Quality Rankings (BLEU & chrF)\n")
    for i, (m, r) in enumerate(scores.sort_values("Quality_Score", ascending=False).iterrows(), 1):
        out.append(f"{i}. **{m}**: {r['Quality_Score']:.3f} "
                   f"(BLEU: {r['BLEU']:.3f}, chrF: {r['chrF']:.1f})")
    out.append("\n## Speed Rankings\n")
    for i, (m, r) in enumerate(scores.sort_values("Response_Time").iterrows(), 1):
        out.append(f"{i}. **{m}**: {r['Response_Time']:.2f}s avg")

    out.append("\n## Per-Language Detail\n")
    out.append("| Model | Language | BLEU | chrF | Avg Time (s) |")
    out.append("|-------|----------|------|------|--------------|")
    per = results_df.groupby(["Model", "Language"]).agg(
        BLEU=("BLEU", "mean"), chrF=("chrF", "mean"),
        T=("Response_Time_Seconds", "mean")).reset_index()
    for _, r in per.iterrows():
        out.append(f"| {r['Model']} | {r['Language']} | {r['BLEU']:.3f} | "
                   f"{r['chrF']:.1f} | {r['T']:.2f} |")
    return "\n".join(out) + "\n"


def maybe_visualize(results_df):
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except Exception:
        print("  (matplotlib/seaborn not installed — skipping charts)")
        return
    if results_df.empty:
        return
    pivot = results_df.pivot_table(values="chrF", index="Model", columns="Language", aggfunc="mean")
    plt.figure(figsize=(14, 5))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlGnBu")
    plt.title("Tiny-Aya chrF by Model and Language")
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, "tiny_aya_chrf_heatmap.png"), dpi=200, bbox_inches="tight")
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Tiny-Aya regional translation bake-off")
    ap.add_argument("--models", nargs="+", default=["global", "fire", "water"],
                    choices=list(TINY_AYA_MODELS.keys()),
                    help="Which regional models to test (default: global fire water; earth skipped — no African ref data)")
    ap.add_argument("--num-phrases", type=int, default=None,
                    help="Limit number of source phrases (default: all)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Run the full pipeline offline with stand-in translations (no API calls)")
    args = ap.parse_args()

    print("🚀 Tiny-Aya Regional Translation Bake-off\n")

    phrases, references = load_reference_data(args.num_phrases)
    available_codes = list(references.keys())
    print(f"Loaded {len(phrases)} phrases × {len(available_codes)} reference languages.\n")

    client = None
    if not args.dry_run:
        import cohere
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            raise SystemExit("COHERE_API_KEY not set. Export it or use --dry-run.")
        client = cohere.Client(api_key)

    cache = load_cache()
    initial_cache = len(cache)
    results = []
    tested = {}
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for region in args.models:
        model_name, model_id = TINY_AYA_MODELS[region]
        langs = languages_for_model(region, available_codes)
        if not langs:
            print(f"⚠️  {model_name}: no reference languages available — skipping.")
            continue
        tested[model_name] = langs
        print(f"▶ {model_name} ({model_id}) on {len(langs)} languages: "
              f"{', '.join(langs)}")

        for code in langs:
            lang_name = LANGUAGE_NAMES[code]
            for i, phrase in enumerate(phrases):
                translation, rt, from_cache = translate(
                    client, model_id, phrase, lang_name, cache, dry_run=args.dry_run)
                if translation is None:
                    print(f"    ✗ failed: {lang_name} phrase {i}")
                    continue
                reference = references[code][i]
                if not isinstance(reference, str) or not reference.strip():
                    continue
                bleu, chrf = score(translation, reference, code)
                results.append({
                    "Model": model_name, "Model ID": model_id,
                    "Language": lang_name, "Lang Code": code,
                    "Source Text": phrase, "Translated Text": translation,
                    "Reference Text": reference, "BLEU": bleu, "chrF": chrf,
                    "Response_Time_Seconds": rt, "From_Cache": from_cache,
                    "Timestamp": timestamp,
                })
        print()

    if not args.dry_run:
        save_cache(cache)
        print(f"✅ Cache updated (+{len(cache) - initial_cache} new entries).")

    if not results:
        print("❌ No results generated.")
        return

    os.makedirs(REPORTS_DIR, exist_ok=True)
    results_df = pd.DataFrame(results)
    csv_path = os.path.join(REPORTS_DIR, "tiny_aya_results.csv")
    results_df.to_csv(csv_path, index=False)
    print(f"✅ Results → {csv_path}")

    maybe_visualize(results_df)

    report = generate_report(results_df, timestamp, tested)
    report_path = os.path.join(REPORTS_DIR, "tiny_aya_bakeoff_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ Report → {report_path}\n")
    print("=" * 60)
    print(report)


if __name__ == "__main__":
    main()

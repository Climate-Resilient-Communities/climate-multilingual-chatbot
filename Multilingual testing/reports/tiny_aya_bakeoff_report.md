# Tiny-Aya Regional Translation Bake-off Report

**Generated:** 2026-06-04 19:34:41

## Executive Summary

Evaluated 3 Tiny-Aya regional models on 18 languages × 8 phrases, each model run on the languages it is routed to in production.

### 🏆 Overall Winner: **Tiny-Aya Water**

Weighted score = Translation Quality (70%) + Response Speed (30%). Cost is omitted (Tiny-Aya pricing not published).

## Models & Language Coverage

- **Tiny-Aya Global** (18 langs): Arabic, Chinese, Russian, Japanese, Hindi, German, French, Spanish, Filipino (Tagalog), Portuguese, Persian, Urdu, Korean, Italian, Tamil, Bengali, Vietnamese, Gujarati
- **Tiny-Aya Fire** (5 langs): Hindi, Urdu, Tamil, Bengali, Gujarati
- **Tiny-Aya Water** (13 langs): Arabic, Chinese, Russian, Japanese, German, French, Spanish, Filipino (Tagalog), Portuguese, Persian, Korean, Italian, Vietnamese

## Quality Rankings (BLEU & chrF)

1. **Tiny-Aya Water**: 0.601 (BLEU: 0.515, chrF: 68.8)
2. **Tiny-Aya Fire**: 0.544 (BLEU: 0.411, chrF: 67.6)
3. **Tiny-Aya Global**: 0.543 (BLEU: 0.449, chrF: 63.7)

## Speed Rankings

1. **Tiny-Aya Water**: 6.23s avg
2. **Tiny-Aya Global**: 6.50s avg
3. **Tiny-Aya Fire**: 7.79s avg

## Per-Language Detail

| Model | Language | BLEU | chrF | Avg Time (s) |
|-------|----------|------|------|--------------|
| Tiny-Aya Fire | Bengali | 0.343 | 63.8 | 6.98 |
| Tiny-Aya Fire | Gujarati | 0.396 | 64.5 | 9.60 |
| Tiny-Aya Fire | Hindi | 0.507 | 71.4 | 6.69 |
| Tiny-Aya Fire | Tamil | 0.356 | 71.1 | 7.38 |
| Tiny-Aya Fire | Urdu | 0.456 | 67.4 | 8.30 |
| Tiny-Aya Global | Arabic | 0.531 | 73.4 | 6.01 |
| Tiny-Aya Global | Bengali | 0.266 | 51.4 | 13.69 |
| Tiny-Aya Global | Chinese | 0.575 | 51.3 | 4.45 |
| Tiny-Aya Global | Filipino (Tagalog) | 0.470 | 74.9 | 7.90 |
| Tiny-Aya Global | French | 0.630 | 81.2 | 6.85 |
| Tiny-Aya Global | German | 0.538 | 75.1 | 6.10 |
| Tiny-Aya Global | Gujarati | 0.315 | 52.0 | 7.43 |
| Tiny-Aya Global | Hindi | 0.533 | 72.5 | 6.53 |
| Tiny-Aya Global | Italian | 0.472 | 67.6 | 5.42 |
| Tiny-Aya Global | Japanese | 0.274 | 40.0 | 4.52 |
| Tiny-Aya Global | Korean | 0.373 | 48.9 | 4.59 |
| Tiny-Aya Global | Persian | 0.492 | 72.6 | 7.40 |
| Tiny-Aya Global | Portuguese | 0.567 | 76.5 | 6.01 |
| Tiny-Aya Global | Russian | 0.454 | 63.8 | 5.66 |
| Tiny-Aya Global | Spanish | 0.513 | 69.8 | 5.35 |
| Tiny-Aya Global | Tamil | 0.358 | 71.4 | 7.32 |
| Tiny-Aya Global | Urdu | 0.449 | 66.5 | 8.14 |
| Tiny-Aya Global | Vietnamese | 0.274 | 37.5 | 3.64 |
| Tiny-Aya Water | Arabic | 0.542 | 74.7 | 6.13 |
| Tiny-Aya Water | Chinese | 0.581 | 51.5 | 4.74 |
| Tiny-Aya Water | Filipino (Tagalog) | 0.475 | 75.3 | 7.97 |
| Tiny-Aya Water | French | 0.638 | 81.4 | 6.93 |
| Tiny-Aya Water | German | 0.542 | 76.5 | 6.30 |
| Tiny-Aya Water | Italian | 0.427 | 60.0 | 4.77 |
| Tiny-Aya Water | Japanese | 0.280 | 41.7 | 4.72 |
| Tiny-Aya Water | Korean | 0.412 | 55.2 | 5.51 |
| Tiny-Aya Water | Persian | 0.505 | 73.7 | 7.59 |
| Tiny-Aya Water | Portuguese | 0.534 | 75.6 | 6.19 |
| Tiny-Aya Water | Russian | 0.511 | 72.9 | 7.12 |
| Tiny-Aya Water | Spanish | 0.632 | 81.0 | 6.06 |
| Tiny-Aya Water | Vietnamese | 0.619 | 74.4 | 6.95 |

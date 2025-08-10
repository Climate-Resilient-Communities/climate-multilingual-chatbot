# Combined Translation Model Bake-off Report

**Generated:** 2025-08-06 15:33:19

## Executive Summary

We evaluated 9 models from AWS Bedrock and Cohere across 18 languages using 8 test phrases. The evaluation focused on translation quality, response time, and cost efficiency.

### 🏆 Overall Winner: **Command Light**

Based on a weighted score combining Translation Quality (50%), Response Speed (30%), and Cost Efficiency (20%).

## Models Tested
- **Nova Pro**: `amazon.nova-pro-v1:0`
- **Nova Micro**: `amazon.nova-micro-v1:0`
- **Nova Lite**: `amazon.nova-lite-v1:0`
- **Titan Text Premier**: `amazon.titan-text-premier-v1:0`
- **Command A**: `command-a-03-2025`
- **Command R7B**: `command-r7b-12-2024`
- **Command Light**: `command-light`
- **Aya Expanse 32B**: `c4ai-aya-expanse-32b`
- **Aya Expanse 8B**: `c4ai-aya-expanse-8b`

## Languages Evaluated
Arabic, Chinese, Russian, Japanese, Hindi, German, French, Spanish, Filipino (Tagalog), Portuguese, Persian, Urdu, Korean, Italian, Tamil, Bengali, Vietnamese, Gujarati

## Key Findings

### 1. Quality Rankings (BLEU & chrF)
1. **Command A**: 0.601 (BLEU: 0.495, chrF: 70.7)
2. **Aya Expanse 32B**: 0.557 (BLEU: 0.452, chrF: 66.3)
3. **Aya Expanse 8B**: 0.515 (BLEU: 0.406, chrF: 62.5)
4. **Nova Pro**: 0.505 (BLEU: 0.405, chrF: 60.6)
5. **Nova Lite**: 0.491 (BLEU: 0.389, chrF: 59.3)
6. **Nova Micro**: 0.472 (BLEU: 0.369, chrF: 57.5)
7. **Command R7B**: 0.429 (BLEU: 0.340, chrF: 51.9)
8. **Command Light**: 0.045 (BLEU: 0.006, chrF: 8.4)

### 2. Speed Rankings
1. **Nova Micro**: 4.03s avg response
2. **Command Light**: 5.53s avg response
3. **Nova Lite**: 5.78s avg response
4. **Nova Pro**: 8.22s avg response
5. **Aya Expanse 8B**: 10.41s avg response
6. **Command R7B**: 12.86s avg response
7. **Aya Expanse 32B**: 17.97s avg response
8. **Command A**: 25.01s avg response

### 3. Cost Rankings (Total Estimated)
1. **Command Light**: $0.00000 total
2. **Nova Micro**: $0.01500 total
3. **Command R7B**: $0.02142 total
4. **Nova Lite**: $0.02568 total
5. **Aya Expanse 8B**: $0.20307 total
6. **Aya Expanse 32B**: $0.20476 total
7. **Nova Pro**: $0.34345 total
8. **Command A**: $0.36042 total

## Detailed Results
### Model Performance Summary
| Model | Avg BLEU | Avg chrF | Avg Response Time (s) | Total Cost ($) | Cache Hits |
|-------|----------|----------|-----------------------|----------------|------------|
| Aya Expanse 32B | 0.452 ± 0.172 | 66.3 ± 14.0 | 17.97 ± 31.74 | 0.20480 | 144 |
| Aya Expanse 8B | 0.406 ± 0.191 | 62.5 ± 15.9 | 10.41 ± 7.71 | 0.20310 | 144 |
| Command A | 0.495 ± 0.159 | 70.7 ± 11.9 | 25.01 ± 44.05 | 0.36040 | 144 |
| Command Light | 0.006 ± 0.018 | 8.4 ± 10.8 | 5.53 ± 8.95 | 0.00000 | 144 |
| Command R7B | 0.340 ± 0.222 | 51.9 ± 25.9 | 12.86 ± 27.76 | 0.02140 | 144 |
| Nova Lite | 0.389 ± 0.199 | 59.3 ± 17.9 | 5.78 ± 1.63 | 0.02570 | 144 |
| Nova Micro | 0.369 ± 0.197 | 57.5 ± 18.3 | 4.03 ± 1.38 | 0.01500 | 0 |
| Nova Pro | 0.405 ± 0.201 | 60.6 ± 17.9 | 8.22 ± 2.77 | 0.34340 | 144 |

## Visualizations
See the `reports` directory for generated charts.

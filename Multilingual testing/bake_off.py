
import json
from dotenv import load_dotenv
import os
load_dotenv()
import time
import pandas as pd
import evaluate
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# --- Configuration ---
# The four models to be tested head-to-head.
# The script will automatically skip any that can't be accessed.
MODELS_TO_TEST = {
    "Nova Pro": "amazon.nova-pro-v1:0",
    "Nova Micro": "amazon.nova-micro-v1:0",
    "Nova Lite": "amazon.nova-lite-v1:0",
    "Titan Text Premier": "amazon.titan-text-premier-v1:0"
}

# Approximate cost per 1K tokens (you should verify these with AWS pricing)
MODEL_COSTS = {
    "amazon.nova-pro-v1:0":      {"input": 0.0008,   "output": 0.0032},
    "amazon.nova-micro-v1:0":    {"input": 0.000035, "output": 0.00014},
    "amazon.nova-lite-v1:0":     {"input": 0.00006,  "output": 0.00024},
    "amazon.titan-text-premier-v1:0": {"input": 0.0005, "output": 0.0015},
}

LANGUAGES = {
    "Arabic": "ar",
    "Chinese (Simplified)": "zh",
    "Russian": "ru",
    "Japanese": "ja",
    "Hindi": "hi",
    "German": "de",
    "French": "fr",
    "Spanish": "es",
    "Filipino (Tagalog)": "tl"
}

TEST_PHRASES = [
    "Climate change is a long-term shift in global weather patterns and temperatures.",
    "What are the most effective strategies for mitigating the impacts of climate change in coastal communities?",
    "Renewable energy sources, such as solar and wind power, are crucial for reducing carbon emissions.",
    "The agricultural sector must adapt to changing climate conditions to ensure food security.",
    "International cooperation is essential for addressing the global challenge of climate change."
]

# In a real-world scenario, these would be high-quality, human-generated translations.
REFERENCE_TRANSLATIONS = {
    "ar": [
        "تغير المناخ هو تحول طويل الأمد في أنماط الطقس ودرجات الحرارة العالمية.",
        "ما هي أكثر الاستراتيجيات فعالية للتخفيف من آثار تغير المناخ في المجتمعات الساحلية؟",
        "تعد مصادر الطاقة المتجددة، مثل الطاقة الشمسية وطاقة الرياح، حاسمة لخفض انبعاثات الكربون.",
        "يجب على القطاع الزراعي التكيف مع الظروف المناخية المتغيرة لضمان الأمن الغذائي.",
        "التعاون الدولي ضروري لمواجهة التحدي العالمي المتمثل في تغير المناخ."
    ],
    "zh": [
        "气候变化是全球天气模式和温度的长期转变。",
        "在沿海社区，减缓气候变化影响最有效的策略是什么？",
        "太阳能和风能等可再生能源对于减少碳排放至关重要。",
        "农业部门必须适应不断变化的气候条件，以确保粮食安全。",
        "国际合作对于应对气候变化的全球挑战至关重要。"
    ],
    "ru": [
        "Изменение климата - это долгосрочное изменение глобальных погодных условий и температур.",
        "Каковы наиболее эффективные стратегии смягчения последствий изменения климата в прибрежных сообществах?",
        "Возобновляемые источники энергии, такие как солнечная и ветровая энергия, имеют решающее значение для сокращения выбросов углерода.",
        "Сельскохозяйственный сектор должен адаптироваться к изменяющимся климатическим условиям для обеспечения продовольственной безопасности.",
        "Международное сотрудничество необходимо для решения глобальной проблемы изменения климата."
    ],
    "ja": [
        "気候変動とは、地球規模の気象パターンと気温の長期的な変化です。",
        "沿岸地域社会における気候変動の影響を緩和するための最も効果的な戦略は何ですか？",
        "太陽光や風力などの再生可能エネルギー源は、炭素排出量を削減するために不可欠です。",
        "食料安全保障を確保するためには、農業部門は変化する気候条件に適応する必要があります。",
        "気候変動という世界的な課題に取り組むためには、国際協力が不可欠です。"
    ],
    "hi": [
        "जलवायु परिवर्तन वैश्विक मौसम पैटर्न और तापमान में एक दीर्घकालिक बदलाव है।",
        "तटीय समुदायों में जलवायु परिवर्तन के प्रभावों को कम करने के लिए सबसे प्रभावी रणनीतियाँ क्या हैं?",
        "सौर और पवन ऊर्जा जैसे नवीकरणीय ऊर्जा स्रोत कार्बन उत्सर्जन को कम करने के लिए महत्वपूर्ण हैं।",
        "खाद्य सुरक्षा सुनिश्चित करने के लिए कृषि क्षेत्र को बदलती जलवायु परिस्थितियों के अनुकूल होना चाहिए।",
        "जलवायु परिवर्तन की वैश्विक चुनौती से निपटने के लिए अंतर्राष्ट्रीय सहयोग आवश्यक है।"
    ],
    "de": [
        "Der Klimawandel ist eine langfristige Veränderung der globalen Wettermuster und Temperaturen.",
        "Was sind die wirksamsten Strategien zur Minderung der Auswirkungen des Klimawandels in Küstengemeinden?",
        "Erneuerbare Energiequellen wie Sonnen- und Windenergie sind entscheidend für die Reduzierung der Kohlenstoffemissionen.",
        "Der Agrarsektor muss sich an die veränderten klimatischen Bedingungen anpassen, um die Ernährungssicherheit zu gewährleisten.",
        "Internationale Zusammenarbeit ist unerlässlich, um die globale Herausforderung des Klimawandels zu bewältigen."
    ],
    "fr": [
        "Le changement climatique est une modification à long terme des régimes météorologiques et des températures mondiales.",
        "Quelles sont les stratégies les plus efficaces pour atténuer les impacts du changement climatique dans les communautés côtières ?",
        "Les sources d'énergie renouvelables, telles que l'énergie solaire et éolienne, sont cruciales pour réduire les émissions de carbone.",
        "Le secteur agricole doit s'adapter aux conditions climatiques changeantes pour assurer la sécurité alimentaire.",
        "La coopération internationale est essentielle pour relever le défi mondial du changement climatique."
    ],
    "es": [
        "El cambio climático es una alteración a largo plazo de los patrones meteorológicos y las temperaturas globales.",
        "¿Cuáles son las estrategias más eficaces para mitigar los impactos del cambio climático en las comunidades costeras?",
        "Las fuentes de energía renovables, como la solar y la eólica, son cruciales para reducir las emisiones de carbono.",
        "El sector agrícola debe adaptarse a las condiciones climáticas cambiantes para garantizar la seguridad alimentaria.",
        "La cooperación internacional es esencial para abordar el desafío global del cambio climático."
    ],
    "tl": [
        "Ang pagbabago ng klima ay isang pangmatagalang pagbabago sa mga pattern ng panahon at temperatura sa buong mundo.",
        "Ano ang mga pinaka-epektibong estratehiya para sa pagpapagaan ng mga epekto ng pagbabago ng klima sa mga komunidad sa baybayin?",
        "Ang mga renewable na pinagkukunan ng enerhiya, tulad ng solar at wind power, ay mahalaga para sa pagbawas ng carbon emissions.",
        "Ang sektor ng agrikultura ay dapat mag-adapt sa mga nagbabagong kondisyon ng klima upang matiyak ang seguridad sa pagkain.",
        "Ang internasyonal na kooperasyon ay mahalaga para sa pagharap sa pandaigdigang hamon ng pagbabago ng klima."
    ]
}

# Cache configuration
CACHE_FILE = 'translation_cache.json'

# Initialize the Boto3 client for Bedrock Runtime (simplified version)
try:
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    bedrock_client = session.client(
        service_name='bedrock-runtime',
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
except Exception as e:
    print(f"Error creating Boto3 client: {e}")
    print("Please ensure your AWS credentials and region are configured correctly.")
    exit()

def load_cache():
    """Load cached translations if available."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save cache to file."""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

def estimate_tokens(text):
    """Rough estimation of tokens (4 chars per token approximation)."""
    return len(text) / 4

def calculate_cost(model_id, input_text, output_text):
    """Calculate estimated cost based on token usage."""
    if model_id not in MODEL_COSTS:
        return 0
    
    input_tokens = estimate_tokens(input_text) / 1000  # Convert to K tokens
    output_tokens = estimate_tokens(output_text) / 1000  # Convert to K tokens
    
    cost = (input_tokens * MODEL_COSTS[model_id]["input"] + 
            output_tokens * MODEL_COSTS[model_id]["output"])
    
    return cost

def translate_text(model_name, model_id, text, target_lang_name, cache):
    """
    Translates text using a specified Bedrock model via Boto3,
    with retries for throttling and graceful failure for access errors.
    """
    # Check cache first
    cache_key = f"{model_id}_{target_lang_name}_{text}"
    if cache_key in cache:
        cached_result = cache[cache_key]
        return cached_result['translation'], cached_result['response_time'], True
    
    prompt = f"""You are a professional translator.
Translate the following English text to {target_lang_name}.
Style: Formal
Tone: Informative
Glossary:
    - "Climate change" should be translated consistently.
    - "Carbon emissions" should be translated consistently.

English text to translate: "{text}"
Translation:"""
    
    # Different request formats for different models
    if "nova" in model_id:
        # Nova models use the messages API format
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 1024,
                "temperature": 0.1,
                "topP": 0.9
            }
        }
    else:
        # Titan models use the older format
        request_body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 1024,
                "temperature": 0.1,
                "topP": 0.9,
                "stopSequences": []
            }
        }

    max_retries = 3
    start_time = time.time()
    
    for attempt in range(max_retries):
        try:
            response = bedrock_client.invoke_model(
                modelId=model_id,
                contentType='application/json',
                accept='application/json',
                body=json.dumps(request_body)
            )
            response_body = json.loads(response['body'].read())
            
            # Different response formats for different models
            if "nova" in model_id:
                # Nova models return content in a different structure
                translation = response_body['output']['message']['content'][0]['text'].strip()
            else:
                # Titan models have results array
                translation = response_body['results'][0]['outputText'].strip()
            
            response_time = time.time() - start_time
            
            # Cache the result
            cache[cache_key] = {
                'translation': translation,
                'response_time': response_time
            }
            
            return translation, response_time, False
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ThrottlingException':
                print(f"  ...Rate limit hit for {model_name}. Retrying in {2**attempt}s...")
                time.sleep(2**attempt)
                continue
            elif error_code in ['AccessDeniedException', 'ValidationException']:
                print(f"  ...SKIPPING {model_name} ({model_id}). Reason: {error_code}.")
                return None, 0, False
            else:
                print(f"  ...An unhandled error occurred for {model_name}: {e}")
                return None, 0, False
    print(f"  ...Failed to get a response from {model_name} after {max_retries} retries.")
    return None, 0, False

def create_visualizations(results_df):
    """Create charts and visualizations for the report."""
    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # 1. Quality Scores Heatmap
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # BLEU scores heatmap
    bleu_pivot = results_df.pivot_table(values='BLEU', index='Model', columns='Language', aggfunc='mean')
    sns.heatmap(bleu_pivot, annot=True, fmt='.3f', cmap='YlGnBu', ax=ax1, vmin=0, vmax=1)
    ax1.set_title('BLEU Scores by Model and Language', fontsize=16, fontweight='bold')
    ax1.set_xlabel('')
    
    # chrF scores heatmap
    chrf_pivot = results_df.pivot_table(values='chrF', index='Model', columns='Language', aggfunc='mean')
    sns.heatmap(chrf_pivot, annot=True, fmt='.3f', cmap='YlOrRd', ax=ax2, vmin=0, vmax=100)
    ax2.set_title('chrF Scores by Model and Language', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('quality_heatmaps.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Performance Metrics
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # Average response time by model
    avg_response_time = results_df.groupby('Model')['Response_Time_Seconds'].mean().sort_values()
    avg_response_time.plot(kind='barh', ax=ax1, color='skyblue')
    ax1.set_title('Average Response Time by Model', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Response Time (seconds)')
    
    # Total cost by model
    total_cost = results_df.groupby('Model')['Estimated_Cost'].sum().sort_values()
    total_cost.plot(kind='barh', ax=ax2, color='lightcoral')
    ax2.set_title('Total Cost by Model', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Cost (USD)')
    
    # Quality vs Speed scatter
    model_summary = results_df.groupby('Model').agg({
        'BLEU': 'mean',
        'chrF': 'mean',
        'Response_Time_Seconds': 'mean'
    })
    model_summary['Combined_Quality'] = (model_summary['BLEU'] + model_summary['chrF']/100) / 2
    
    ax3.scatter(model_summary['Response_Time_Seconds'], model_summary['Combined_Quality'], s=200)
    for idx, row in model_summary.iterrows():
        ax3.annotate(idx, (row['Response_Time_Seconds'], row['Combined_Quality']), 
                    ha='center', va='bottom', fontsize=10)
    ax3.set_xlabel('Average Response Time (seconds)')
    ax3.set_ylabel('Combined Quality Score')
    ax3.set_title('Quality vs Speed Trade-off', fontsize=14, fontweight='bold')
    
    # Cost vs Quality scatter
    model_cost_quality = results_df.groupby('Model').agg({
        'Combined_Score': 'mean',
        'Estimated_Cost': 'sum'
    })
    
    ax4.scatter(model_cost_quality['Estimated_Cost'], model_cost_quality['Combined_Score'], s=200, color='green')
    for idx, row in model_cost_quality.iterrows():
        ax4.annotate(idx, (row['Estimated_Cost'], row['Combined_Score']), 
                    ha='center', va='bottom', fontsize=10)
    ax4.set_xlabel('Total Cost (USD)')
    ax4.set_ylabel('Average Combined Score')
    ax4.set_title('Cost vs Quality Trade-off', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('performance_metrics.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Language-specific performance
    fig, ax = plt.subplots(figsize=(12, 6))
    
    lang_perf = results_df.groupby(['Language', 'Model'])['Combined_Score'].mean().unstack()
    lang_perf.plot(kind='bar', ax=ax, width=0.8)
    ax.set_title('Model Performance by Language', fontsize=16, fontweight='bold')
    ax.set_xlabel('Language')
    ax.set_ylabel('Combined Score')
    ax.legend(title='Model', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig('language_performance.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_report(results_df, timestamp):
    """Generate a comprehensive markdown report."""
    
    # Calculate summary statistics
    model_summary = results_df.groupby('Model').agg({
        'BLEU': ['mean', 'std'],
        'chrF': ['mean', 'std'],
        'Response_Time_Seconds': ['mean', 'std'],
        'Estimated_Cost': 'sum',
        'From_Cache': 'sum'
    }).round(3)
    
    # Calculate combined scores and rankings
    model_scores = results_df.groupby('Model').agg({
        'BLEU': 'mean',
        'chrF': 'mean',
        'Response_Time_Seconds': 'mean',
        'Estimated_Cost': 'sum'
    })
    
    # Normalize scores for fair comparison
    model_scores['Quality_Score'] = (model_scores['BLEU'] + model_scores['chrF']/100) / 2
    model_scores['Speed_Score'] = 1 / (1 + model_scores['Response_Time_Seconds'])
    model_scores['Cost_Efficiency'] = model_scores['Quality_Score'] / (model_scores['Estimated_Cost'] + 0.0001)
    model_scores['Overall_Score'] = (model_scores['Quality_Score'] * 0.5 + 
                                     model_scores['Speed_Score'] * 0.3 + 
                                     model_scores['Cost_Efficiency'] * 0.2)
    
    winner = model_scores['Overall_Score'].idxmax()
    
    report = f"""# AWS Bedrock Translation Model Bake-off Report

**Generated:** {timestamp}

## Executive Summary

We evaluated {len(MODELS_TO_TEST)} AWS Bedrock models across {len(LANGUAGES)} languages using {len(TEST_PHRASES)} test phrases for multilingual translation capabilities. The evaluation focused on translation quality, response time, and cost efficiency.

### 🏆 Overall Winner: **{winner}**

Based on a weighted score combining:
- Translation Quality (50%)
- Response Speed (30%)  
- Cost Efficiency (20%)

## Models Tested
"""
    
    for model_name, model_id in MODELS_TO_TEST.items():
        report += f"- **{model_name}**: `{model_id}`\n"
    
    report += f"""
## Languages Evaluated
{', '.join(LANGUAGES.keys())}

## Key Findings

### 1. Quality Metrics (BLEU & chrF)
"""
    
    # Add quality rankings
    quality_rankings = model_scores.sort_values('Quality_Score', ascending=False)
    for idx, (model, row) in enumerate(quality_rankings.iterrows(), 1):
        report += f"{idx}. **{model}**: {row['Quality_Score']:.3f} (BLEU: {row['BLEU']:.3f}, chrF: {row['chrF']:.1f})\n"
    
    report += """
### 2. Performance Metrics
"""
    
    # Add performance rankings
    speed_rankings = model_scores.sort_values('Response_Time_Seconds')
    for idx, (model, row) in enumerate(speed_rankings.iterrows(), 1):
        report += f"{idx}. **{model}**: {row['Response_Time_Seconds']:.2f}s average response time\n"
    
    report += """
### 3. Cost Analysis
"""
    
    # Add cost rankings
    cost_rankings = model_scores.sort_values('Estimated_Cost')
    for idx, (model, row) in enumerate(cost_rankings.iterrows(), 1):
        report += f"{idx}. **{model}**: ${row['Estimated_Cost']:.4f} total cost\n"
    
    report += f"""
## Detailed Results

### Model Performance Summary

| Model | Avg BLEU | Avg chrF | Avg Response Time (s) | Total Cost ($) | Cache Hits |
|-------|----------|----------|----------------------|----------------|------------|
"""
    
    for model in model_summary.index:
        row = model_summary.loc[model]
        report += f"| {model} | {row['BLEU']['mean']:.3f} ± {row['BLEU']['std']:.3f} | "
        report += f"{row['chrF']['mean']:.1f} ± {row['chrF']['std']:.1f} | "
        report += f"{row['Response_Time_Seconds']['mean']:.2f} ± {row['Response_Time_Seconds']['std']:.2f} | "
        report += f"{row['Estimated_Cost']['sum']:.4f} | {int(row['From_Cache']['sum'])} |\n"
    
    # Language-specific insights
    report += """
### Language-Specific Performance

"""
    
    lang_performance = results_df.groupby(['Language', 'Model'])['Combined_Score'].mean().unstack()
    best_model_per_lang = lang_performance.idxmax(axis=1)
    
    report += "| Language | Best Performing Model | Score |\n"
    report += "|----------|----------------------|-------|\n"
    for lang, model in best_model_per_lang.items():
        score = lang_performance.loc[lang, model]
        report += f"| {lang} | {model} | {score:.3f} |\n"
    
    # Add recommendations
    report += f"""
## Recommendations

### For High-Quality Requirements
**Recommended:** {quality_rankings.index[0]}
- Best overall translation quality
- Consistent performance across languages

### For Real-Time Applications
**Recommended:** {speed_rankings.index[0]}
- Fastest response times
- Suitable for interactive applications

### For Budget-Conscious Deployments
**Recommended:** {cost_rankings.index[0]}
- Most cost-effective option
- Good quality-to-cost ratio

### Balanced Choice
**Recommended:** {winner}
- Best overall combination of quality, speed, and cost
- Suitable for most use cases

## Technical Notes

- **Caching**: Results were cached to reduce API calls and costs on repeated runs
- **Token Estimation**: Based on 4 characters per token approximation
- **Cost Calculation**: Using AWS Bedrock pricing as of the test date
- **Quality Metrics**: 
  - BLEU: Measures n-gram precision
  - chrF: Character-level F-score, better for morphologically rich languages

## Visualizations

See the following generated charts:
- `quality_heatmaps.png`: BLEU and chrF scores by model and language
- `performance_metrics.png`: Response time, cost, and trade-off analyses
- `language_performance.png`: Model performance breakdown by language
"""
    
    return report

def main():
    """
    Main function to run the translation bake-off.
    """
    print("🚀 Starting AWS Bedrock Translation Model Bake-off\n")
    
    results = []
    bleu = evaluate.load('bleu')
    chrf = evaluate.load('chrf')
    
    # Load cache
    cache = load_cache()
    initial_cache_size = len(cache)
    
    # Keep track of models that have already failed to avoid re-printing skip messages
    skipped_models = set()
    
    # Calculate total operations for progress bar
    total_operations = sum(1 for _ in MODELS_TO_TEST.items() for _ in LANGUAGES.items() for _ in TEST_PHRASES)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with tqdm(total=total_operations, desc="Translation Progress", unit="translation") as pbar:
        for model_name, model_id in MODELS_TO_TEST.items():
            if model_id in skipped_models:
                pbar.update(len(LANGUAGES) * len(TEST_PHRASES))
                continue

            for lang_name, lang_code in LANGUAGES.items():
                for i, phrase in enumerate(TEST_PHRASES):
                    translation, response_time, from_cache = translate_text(
                        model_name, model_id, phrase, lang_name, cache
                    )

                    if translation:
                        reference = REFERENCE_TRANSLATIONS[lang_code][i]
                        bleu_result = bleu.compute(predictions=[translation], references=[reference])
                        bleu_score = bleu_result['bleu'] if bleu_result and 'bleu' in bleu_result and bleu_result['bleu'] is not None else 0.0
                        chrf_result = chrf.compute(predictions=[translation], references=[reference])
                        chrf_score = chrf_result['score'] if chrf_result and 'score' in chrf_result and chrf_result['score'] is not None else 0.0
                        
                        # Calculate cost
                        prompt = f"""
    You are a professional translator.
    Translate the following English text to {lang_name}.
    Style: Formal
    Tone: Informative
    Glossary:
        - "Climate change" should be translated consistently.
        - "Carbon emissions" should be translated consistently.

    English text to translate: "{phrase}"
    Translation:
    """
                        estimated_cost = calculate_cost(model_id, prompt, translation)
                        
                        results.append({
                            "Model": model_name,
                            "Model ID": model_id,
                            "Language": lang_name,
                            "Language_Code": lang_code,
                            "Source Text": phrase,
                            "Translated Text": translation,
                            "Reference Text": reference,
                            "BLEU": bleu_score,
                            "chrF": chrf_score,
                            "Combined_Score": (bleu_score + chrf_score/100) / 2,
                            "Response_Time_Seconds": response_time,
                            "Estimated_Cost": estimated_cost,
                            "From_Cache": from_cache,
                            "Timestamp": timestamp
                        })
                    else:
                        # If translation failed (e.g., was skipped), add to skipped set
                        skipped_models.add(model_id)
                        # Update progress bar for remaining operations of this model
                        lang_values = list(LANGUAGES.values())
                        remaining_updates = (len(LANGUAGES) - lang_values.index(lang_code)) * len(TEST_PHRASES) - i - 1
                        pbar.update(remaining_updates)
                        break
                    
                    pbar.update(1)
                
                if model_id in skipped_models:
                    break

    # Save cache
    save_cache(cache)
    new_cache_entries = len(cache) - initial_cache_size
    print(f"\n✅ Cache updated with {new_cache_entries} new entries")

    # --- Save results to JSON file ---
    output_filename = 'translation_results.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"✅ Results saved to {output_filename}")

    # --- Reporting ---
    if not results:
        print("\n❌ No results were generated. All models may have been skipped or failed.")
        return

    results_df = pd.DataFrame(results)
    
    # Save to CSV for easy analysis
    results_df.to_csv('translation_results.csv', index=False)
    print("✅ Results saved to translation_results.csv")
    
    # Create visualizations
    print("\n📊 Generating visualizations...")
    create_visualizations(results_df)
    print("✅ Visualizations saved")
    
    # Generate report
    print("\n📝 Generating comprehensive report...")
    report = generate_report(results_df, timestamp)
    
    with open('translation_bakeoff_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    print("✅ Report saved to translation_bakeoff_report.md")
    
    # Print summary to console
    print("\n" + "="*60)
    print("TRANSLATION BAKE-OFF SUMMARY")
    print("="*60)
    
    model_summary = results_df.groupby('Model').agg({
        'BLEU': 'mean',
        'chrF': 'mean',
        'Response_Time_Seconds': 'mean',
        'Estimated_Cost': 'sum'
    }).round(3)
    
    print("\nModel Performance Summary:")
    print(model_summary)
    
    # Calculate winner
    model_summary['Combined_Score'] = (model_summary['BLEU'] + model_summary['chrF']/100) / 2
    winner = model_summary['Combined_Score'].idxmax()
    
    print(f"\n🏆 Overall Winner: {winner}")
    print(f"   - Best Combined Score: {model_summary.loc[winner, 'Combined_Score']:.3f}")
    print(f"   - Average BLEU: {model_summary.loc[winner, 'BLEU']:.3f}")
    print(f"   - Average chrF: {model_summary.loc[winner, 'chrF']:.1f}")
    print(f"   - Average Response Time: {model_summary.loc[winner, 'Response_Time_Seconds']:.2f}s")
    print(f"   - Total Cost: ${model_summary.loc[winner, 'Estimated_Cost']:.4f}")
    
    # Show cost savings from caching
    cache_hits = results_df['From_Cache'].sum()
    if cache_hits > 0:
        estimated_savings = results_df[results_df['From_Cache']]['Estimated_Cost'].sum()
        print(f"\n💰 Cache Performance:")
        print(f"   - Cache Hits: {cache_hits}/{len(results_df)} ({cache_hits/len(results_df)*100:.1f}%)")
        print(f"   - Estimated Savings: ${estimated_savings:.4f}")
    
    print("\n✅ Bake-off Complete! Check the following files for detailed results:")
    print("   - translation_bakeoff_report.md (Comprehensive Report)")
    print("   - translation_results.json (Raw Results)")
    print("   - translation_results.csv (Spreadsheet Format)")
    print("   - quality_heatmaps.png (Visual Quality Comparison)")
    print("   - performance_metrics.png (Performance Analysis)")
    print("   - language_performance.png (Language-specific Results)")


if __name__ == "__main__":
    main()
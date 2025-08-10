import json
from dotenv import load_dotenv
import os
load_dotenv()
import time
import pandas as pd
import evaluate
import boto3
from botocore.exceptions import ClientError
import cohere
from datetime import datetime
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# --- Configuration ---
# Combined list of models to be tested head-to-head.
# The script will automatically skip any that can't be accessed.
MODELS_TO_TEST = {
    # From AWS Bedrock
    "Nova Pro": "amazon.nova-pro-v1:0",
    "Nova Micro": "amazon.nova-micro-v1:0",
    "Nova Lite": "amazon.nova-lite-v1:0",
    "Titan Text Premier": "amazon.titan-text-premier-v1:0",
    # From Cohere
    "Command A": "command-a-03-2025",
    "Command R7B": "command-r7b-12-2024",
    "Command Light": "command-light",
    "Aya Expanse 32B": "c4ai-aya-expanse-32b",
    "Aya Expanse 8B": "c4ai-aya-expanse-8b"
}

# Approximate cost per 1M tokens (verify with provider pricing)
MODEL_COSTS = {
    # AWS Bedrock
    "amazon.nova-pro-v1:0":      {"input": 0.0008,   "output": 0.0032},
    "amazon.nova-micro-v1:0":    {"input": 0.000035, "output": 0.00014},
    "amazon.nova-lite-v1:0":     {"input": 0.00006,  "output": 0.00024},
    "amazon.titan-text-premier-v1:0": {"input": 0.0005, "output": 0.0015},
    # Cohere
    "command-a-03-2025": {"input": 0.0025, "output": 0.001},
    "command-r7b-12-2024": {"input": 0.0000375, "output": 0.00015},
    "c4ai-aya-expanse-32b": {"input": 0.0005, "output": 0.0015},
    "c4ai-aya-expanse-8b": {"input": 0.0005, "output": 0.0015},
}

# Using the more extensive language list
LANGUAGES = {
    "Arabic": "ar", "Chinese": "zh", "Russian": "ru", "Japanese": "ja",
    "Hindi": "hi", "German": "de", "French": "fr", "Spanish": "es",
    "Filipino (Tagalog)": "tl", "Portuguese": "pt", "Persian": "fa",
    "Urdu": "ur", "Korean": "ko", "Italian": "it", "Tamil": "ta",
    "Bengali": "bn", "Vietnamese": "vi", "Gujarati": "gu",
}

# --- Load Source Text and Reference Translations from CSV ---
try:
    translation_OPENAI_df = pd.read_csv('Multilingual testing/translated_OPENAI.csv')
    TEST_PHRASES = translation_OPENAI_df['en_source_text'].tolist()
    REFERENCE_TRANSLATIONS = {}
    for lang_code in list(LANGUAGES.values()):
        column_name = f"{lang_code}_translated_OPENAI"
        if column_name in translation_OPENAI_df:
            REFERENCE_TRANSLATIONS[lang_code] = translation_OPENAI_df[column_name].tolist()
        else:
            print(f"Warning: Reference translations for language '{lang_code}' not found in CSV.")
            LANGUAGES = {k: v for k, v in LANGUAGES.items() if v != lang_code} # Remove lang if no reference
except FileNotFoundError:
    print("Error: 'translated_OPENAI.csv' not found. Please ensure the file is in the correct directory.")
    exit()


# --- Cache Configuration ---
# Store cache alongside this script so it works regardless of current working directory
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'translation_cache.json')

# --- Client Initialization ---
# Initialize Boto3 client for Bedrock
try:
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    bedrock_client = session.client(service_name='bedrock-runtime')
except Exception as e:
    print(f"Could not create Boto3 client: {e}. AWS models will be skipped.")
    bedrock_client = None

# Initialize Cohere client
try:
    cohere_api_key = os.getenv("COHERE_API_KEY")
    if not cohere_api_key:
        raise ValueError("COHERE_API_KEY environment variable not set.")
    cohere_client = cohere.Client(api_key=cohere_api_key)
except Exception as e:
    print(f"Could not create Cohere client: {e}. Cohere models will be skipped.")
    cohere_client = None

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
    Translates text using a specified model, handling both AWS Bedrock and Cohere APIs.
    """
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
    
    max_retries = 3
    start_time = time.time()
    translation = None
    response_time = 0

    # --- AWS Bedrock Models ---
    if "amazon." in model_id:
        if not bedrock_client:
            print(f"  ...SKIPPING {model_name} (AWS client not available).")
            return None, 0, False
        
        if "nova" in model_id:
            request_body = {"messages": [{"role": "user","content": [{"text": prompt}]}],"inferenceConfig": {"maxTokens": 1024, "temperature": 0.1, "topP": 0.9}}
        else: # Titan
            request_body = {"inputText": prompt,"textGenerationConfig": {"maxTokenCount": 1024, "temperature": 0.1, "topP": 0.9, "stopSequences": []}}

        for attempt in range(max_retries):
            try:
                response = bedrock_client.invoke_model(modelId=model_id, contentType='application/json', accept='application/json', body=json.dumps(request_body))
                response_body = json.loads(response['body'].read())
                
                if "nova" in model_id:
                    translation = response_body['output']['message']['content'][0]['text'].strip()
                else:
                    translation = response_body['results'][0]['outputText'].strip()
                break 
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ThrottlingException':
                    print(f"  ...Rate limit for {model_name}. Retrying in {2**attempt}s...")
                    time.sleep(2**attempt)
                elif error_code in ['AccessDeniedException', 'ValidationException']:
                    print(f"  ...SKIPPING {model_name} ({model_id}). Reason: {error_code}.")
                    return None, 0, False
                else:
                    print(f"  ...Unhandled error for {model_name}: {e}")
                    return None, 0, False
        if not translation:
             print(f"  ...Failed to get response from {model_name} after retries.")


    # --- Cohere Models ---
    elif "command" in model_id or "aya" in model_id:
        if not cohere_client:
            print(f"  ...SKIPPING {model_name} (Cohere client not available).")
            return None, 0, False
        
        preamble = f"You are a professional translator. Translate the following English text to {target_lang_name}. Style: Formal. Tone: Informative"
        message = f'English text to translate: "{text}"\nTranslation:'

        for attempt in range(max_retries):
            try:
                response = cohere_client.chat(model=model_id, message=message, preamble=preamble, temperature=0.1)
                translation = response.text
                break
            except Exception as e:
                print(f"  ...Error with {model_name}: {e}. Retrying in {2**attempt}s...")
                time.sleep(2**attempt)
        if not translation:
            print(f"  ...Failed to get response from {model_name} after retries.")

    else:
        print(f"  ...SKIPPING {model_name} ({model_id}). Unknown provider.")
        return None, 0, False

    if translation:
        response_time = time.time() - start_time
        cache[cache_key] = {'translation': translation, 'response_time': response_time}
        return translation, response_time, False
    
    return None, 0, False


def create_visualizations(results_df):
    """Create charts and visualizations for the report."""
    if results_df.empty:
        return
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Ensure the reports directory exists
    os.makedirs("reports", exist_ok=True)

    # 1. Quality Scores Heatmap
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
    
    bleu_pivot = results_df.pivot_table(values='BLEU', index='Model', columns='Language', aggfunc='mean')
    sns.heatmap(bleu_pivot, annot=True, fmt='.3f', cmap='YlGnBu', ax=ax1, vmin=0, vmax=1)
    ax1.set_title('BLEU Scores by Model and Language', fontsize=16, fontweight='bold')
    ax1.set_xlabel('')
    
    chrf_pivot = results_df.pivot_table(values='chrF', index='Model', columns='Language', aggfunc='mean')
    sns.heatmap(chrf_pivot, annot=True, fmt='.3f', cmap='YlOrRd', ax=ax2, vmin=0, vmax=100)
    ax2.set_title('chrF Scores by Model and Language', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('reports/quality_heatmaps.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Performance Metrics
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    avg_response_time = results_df.groupby('Model')['Response_Time_Seconds'].mean().sort_values()
    avg_response_time.plot(kind='barh', ax=ax1, color='skyblue')
    ax1.set_title('Average Response Time by Model', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Response Time (seconds)')
    
    total_cost = results_df.groupby('Model')['Estimated_Cost'].sum().sort_values()
    total_cost.plot(kind='barh', ax=ax2, color='lightcoral')
    ax2.set_title('Total Estimated Cost by Model', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Cost (USD)')
    
    model_summary = results_df.groupby('Model').agg(
        Combined_Quality=('Combined_Score', 'mean'),
        Response_Time_Seconds=('Response_Time_Seconds', 'mean'),
        Estimated_Cost=('Estimated_Cost', 'sum')
    ).reset_index()

    sns.scatterplot(data=model_summary, x='Response_Time_Seconds', y='Combined_Quality', hue='Model', s=200, ax=ax3, legend=False)
    for _, row in model_summary.iterrows():
        ax3.annotate(row['Model'], (row['Response_Time_Seconds'], row['Combined_Quality']), ha='center', va='bottom', fontsize=9)
    ax3.set_xlabel('Average Response Time (seconds)')
    ax3.set_ylabel('Combined Quality Score')
    ax3.set_title('Quality vs Speed Trade-off', fontsize=14, fontweight='bold')

    sns.scatterplot(data=model_summary, x='Estimated_Cost', y='Combined_Quality', hue='Model', s=200, ax=ax4, legend=False, palette='viridis')
    for _, row in model_summary.iterrows():
        ax4.annotate(row['Model'], (row['Estimated_Cost'], row['Combined_Quality']), ha='center', va='bottom', fontsize=9)
    ax4.set_xlabel('Total Cost (USD)')
    ax4.set_ylabel('Combined Quality Score')
    ax4.set_title('Cost vs Quality Trade-off', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('reports/performance_metrics.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Language-specific performance
    fig, ax = plt.subplots(figsize=(14, 7))
    
    lang_perf = results_df.groupby(['Language', 'Model'])['Combined_Score'].mean().unstack()
    lang_perf.plot(kind='bar', ax=ax, width=0.8)
    ax.set_title('Model Performance by Language', fontsize=16, fontweight='bold')
    ax.set_xlabel('Language')
    ax.set_ylabel('Combined Score')
    ax.legend(title='Model', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig('reports/language_performance.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_report(results_df, timestamp):
    """Generate a comprehensive markdown report."""
    if results_df.empty:
        return "No results were generated."

    model_summary = results_df.groupby('Model').agg({
        'BLEU': ['mean', 'std'], 'chrF': ['mean', 'std'],
        'Response_Time_Seconds': ['mean', 'std'], 'Estimated_Cost': 'sum',
        'From_Cache': 'sum'
    }).round(4)
    
    model_scores = results_df.groupby('Model').agg({
        'BLEU': 'mean', 'chrF': 'mean',
        'Response_Time_Seconds': 'mean', 'Estimated_Cost': 'sum'
    })
    
    model_scores['Quality_Score'] = (model_scores['BLEU'] + model_scores['chrF']/100) / 2
    model_scores['Speed_Score'] = 1 / (1 + model_scores['Response_Time_Seconds'])
    model_scores['Cost_Efficiency'] = model_scores['Quality_Score'] / (model_scores['Estimated_Cost'] + 1e-6)
    model_scores['Overall_Score'] = (model_scores['Quality_Score'] * 0.5 +
                                     model_scores['Speed_Score'] * 0.3 +
                                     model_scores['Cost_Efficiency'] * 0.2)
    
    winner = model_scores['Overall_Score'].idxmax()
    
    report = f"""# Combined Translation Model Bake-off Report

**Generated:** {timestamp}

## Executive Summary

We evaluated {len(MODELS_TO_TEST)} models from AWS Bedrock and Cohere across {len(LANGUAGES)} languages using {len(TEST_PHRASES)} test phrases. The evaluation focused on translation quality, response time, and cost efficiency.

### 🏆 Overall Winner: **{winner}**

Based on a weighted score combining Translation Quality (50%), Response Speed (30%), and Cost Efficiency (20%).

## Models Tested
"""
    for model_name, model_id in MODELS_TO_TEST.items():
        report += f"- **{model_name}**: `{model_id}`\n"
    
    report += f"\n## Languages Evaluated\n{', '.join(LANGUAGES.keys())}\n"
    
    report += "\n## Key Findings\n"
    quality_rankings = model_scores.sort_values('Quality_Score', ascending=False)
    report += "\n### 1. Quality Rankings (BLEU & chrF)\n"
    for i, (model, row) in enumerate(quality_rankings.iterrows(), 1):
        report += f"{i}. **{model}**: {row['Quality_Score']:.3f} (BLEU: {row['BLEU']:.3f}, chrF: {row['chrF']:.1f})\n"

    speed_rankings = model_scores.sort_values('Response_Time_Seconds')
    report += "\n### 2. Speed Rankings\n"
    for i, (model, row) in enumerate(speed_rankings.iterrows(), 1):
        report += f"{i}. **{model}**: {row['Response_Time_Seconds']:.2f}s avg response\n"

    cost_rankings = model_scores.sort_values('Estimated_Cost')
    report += "\n### 3. Cost Rankings (Total Estimated)\n"
    for i, (model, row) in enumerate(cost_rankings.iterrows(), 1):
        report += f"{i}. **{model}**: ${row['Estimated_Cost']:.5f} total\n"

    report += "\n## Detailed Results\n### Model Performance Summary\n"
    report += "| Model | Avg BLEU | Avg chrF | Avg Response Time (s) | Total Cost ($) | Cache Hits |\n"
    report += "|-------|----------|----------|-----------------------|----------------|------------|\n"
    for model in model_summary.index:
        row = model_summary.loc[model]
        report += f"| {model} | {row['BLEU']['mean']:.3f} \u00b1 {row['BLEU']['std']:.3f} | "
        report += f"{row['chrF']['mean']:.1f} \u00b1 {row['chrF']['std']:.1f} | "
        report += f"{row['Response_Time_Seconds']['mean']:.2f} \u00b1 {row['Response_Time_Seconds']['std']:.2f} | "
        report += f"{row['Estimated_Cost']['sum']:.5f} | {int(row['From_Cache']['sum'])} |\n"
    
    report += "\n## Visualizations\nSee the `reports` directory for generated charts.\n"
    return report

def main():
    """Main function to run the combined translation bake-off."""
    print("\U0001f680 Starting Combined AWS & Cohere Translation Model Bake-off\n")
    
    results = []
    bleu = evaluate.load('bleu')
    chrf = evaluate.load('chrf')
    cache = load_cache()
    initial_cache_size = len(cache)
    skipped_models = set()
    
    total_operations = len(MODELS_TO_TEST) * len(LANGUAGES) * len(TEST_PHRASES)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with tqdm(total=total_operations, desc="Translation Progress", unit="t") as pbar:
        for model_name, model_id in MODELS_TO_TEST.items():
            if model_id in skipped_models:
                pbar.update(len(LANGUAGES) * len(TEST_PHRASES))
                continue

            for lang_name, lang_code in LANGUAGES.items():
                for i, phrase in enumerate(TEST_PHRASES):
                    pbar.set_description(f"{model_name} ({lang_name})")
                    translation, response_time, from_cache = translate_text(
                        model_name, model_id, phrase, lang_name, cache
                    )

                    if translation:
                        reference = REFERENCE_TRANSLATIONS[lang_code][i]
                        bleu_score = bleu.compute(predictions=[translation], references=[[reference]])['bleu']
                        chrf_score = chrf.compute(predictions=[translation], references=[[reference]])['score']
                        
                        prompt_for_cost = f'Translate "{phrase}" to {lang_name}'
                        estimated_cost = calculate_cost(model_id, prompt_for_cost, translation)
                        
                        results.append({
                            "Model": model_name, "Model ID": model_id, "Language": lang_name,
                            "Source Text": phrase, "Translated Text": translation, "Reference Text": reference,
                            "BLEU": bleu_score, "chrF": chrf_score,
                            "Combined_Score": (bleu_score + chrf_score/100) / 2,
                            "Response_Time_Seconds": response_time, "Estimated_Cost": estimated_cost,
                            "From_Cache": from_cache, "Timestamp": timestamp
                        })
                    else:
                        skipped_models.add(model_id)
                        remaining_in_lang = len(TEST_PHRASES) - (i + 1)
                        pbar.update(remaining_in_lang)
                        break 
                    
                    pbar.update(1)
                
                if model_id in skipped_models:
                    remaining_langs = list(LANGUAGES.keys()).index(lang_name)
                    pbar.update((len(LANGUAGES) - remaining_langs -1) * len(TEST_PHRASES))
                    break

    save_cache(cache)
    print(f"\n\u2705 Cache updated with {len(cache) - initial_cache_size} new entries.")

    if not results:
        print("\n\u274c No results generated. All models may have been skipped or failed.")
        return

    results_df = pd.DataFrame(results)
    os.makedirs("reports", exist_ok=True)
    results_df.to_csv('reports/translation_results.csv', index=False)
    print("\u2705 Results saved to reports/translation_results.csv")
    
    print("\n\U0001f4ca Generating visualizations...")
    create_visualizations(results_df)
    print("\u2705 Visualizations saved to `reports` directory.")
    
    print("\n\U0001f4dd Generating comprehensive report...")
    report = generate_report(results_df, timestamp)
    with open('reports/translation_bakeoff_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    print("\u2705 Report saved to reports/translation_bakeoff_report.md")
    
    print("\n" + "="*60)
    print("BAKE-OFF SUMMARY")
    print("="*60)
    print(report)

if __name__ == "__main__":
    main()

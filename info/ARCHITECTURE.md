## System Architecture

The diagram below reflects the current architecture after recent refactors (consent modal overlay, LLM JSON query rewriter, canned responses, Pinecone retrieval with BGE-M3, Cohere rerank/faithfulness, Azure blob logging, and multilingual support).

```mermaid
flowchart TD
  U["User"] --> UI["Streamlit UI\n`src/webui/app_nova.py`\n- Consent modal overlay (@st.dialog)\n- Sidebar (dark), chat history + download icon\n- Feedback link (Google Form)"]

  UI --> MN["MultilingualClimateChatbot\n`src/main_nova.py`"]
  MN --> CP["ClimateQueryPipeline\n`src/models/climate_pipeline.py`"]

  CP --> QR["Query Rewriter (LLM JSON)\n`src/models/query_rewriter.py`\n- Detects: greeting, goodbye, thanks, emergency, instruction, on-topic, off-topic, harmful\n- Outputs: classification, rewrite_en, ask_how_to_use, how_it_works"]

  QR -- canned intent --> CANNED["Canned response\n(translate via Nova if needed)\nReturn to UI"]
  QR -- instruction --> HOWTO["Show 'How It Works' text\nReturn to UI"]
  QR -- on-topic --> ROUTE["Language Router\n`src/models/query_routing.py`"]

  ROUTE --> RET["Retrieval\n`src/models/retrieval.py`\n- Pinecone index\n- Embeddings: BGE-M3 (FlagEmbedding)"]
  RET --> RR["Rerank\n`src/models/rerank.py`\n- Cohere Rerank"]
  RR --> GEN["Response Generation\n`src/models/gen_response_nova.py`\n- BedrockModel (Nova)"]

  GEN --> QG["Quality Checks\n`src/models/hallucination_guard.py`\n- Faithfulness (Cohere)"]
  QG -- ok --> TL["Translate to target language (if needed)\nBedrock Nova"]
  QG -- low faithfulness --> TAV["Fallback Search\n(Tavily via `main_nova.py`)"]
  TAV --> TL

  TL --> UIRET["Return response + citations to UI"]
  CANNED --> UI
  HOWTO --> UI
  UIRET --> UI

  subgraph Support & Config
    ENV["Environment Loader\n`src/utils/env_loader.py`\n`src/data/config/azure_config.py`"]
    LANGS["Languages mapping\n`src/utils/languages.json`\nMappings in `src/main_nova.py`"]
    LOGS["Azure Blob Logging\n(Feedback / diagnostics if configured)"]
  end

  ENV --> MN
  LANGS --> MN
  UI -. feedback/metrics .-> LOGS
  RET -. optional diagnostics .-> LOGS
```

Notes
- Canned intents (greeting/goodbye/thanks/emergency) bypass retrieval and generation, returning quickly with translated canned text.
- Instruction queries short-circuit to a fixed help text.
- Off-topic/harmful are handled per pipeline checks.
- Local JSONL logs are disabled by default; Azure blob logging remains available when configured.



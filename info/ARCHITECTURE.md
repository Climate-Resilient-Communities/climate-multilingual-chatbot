## System Architecture

The diagram below reflects the current architecture after recent refactors (consent modal overlay, LLM JSON query rewriter, canned responses, Pinecone retrieval with BGE-M3, Cohere rerank/faithfulness, Azure blob logging, and multilingual support).

```mermaid
flowchart TD
  U["User"] --> UI["Streamlit UI\n`src/webui/app_nova.py`\n- Consent modal (@st.dialog)\n- Sidebar (dark) + chat history icon\n- Feedback (Google Form)"]

  UI --> MN["MultilingualClimateChatbot\n`src/main_nova.py`"]
  MN --> CP["ClimateQueryPipeline\n`src/models/climate_pipeline.py`"]

  CP --> QR["Query Rewriter (LLM JSON)\n`src/models/query_rewriter.py`\n- Detects: greeting, goodbye, thanks, emergency, instruction, on/off-topic/harmful\n- Outputs: classification, rewrite_en, ask_how_to_use, how_it_works"]

  QR -- canned intent --> CANNED["Canned response\n(Translated to user language)"]
  QR -- instruction --> HOWTO["Show 'How It Works' text"]
  QR -- on-topic --> ROUTE["Language Router\n`src/models/query_routing.py`\n- Determines model: Nova vs Command‑A\n- Decides translation provider"]

  ROUTE --> MT{Model Type?}
  MT -- Command‑A --> PRE_COH["Translate to English\n(Command‑A)"]
  MT -- Nova --> PRE_NOVA["Translate to English\n(Nova)"]

  PRE_COH --> RET["Retrieval\n`src/models/retrieval.py`\n- Pinecone + BGE‑M3"]
  PRE_NOVA --> RET
  RET --> RR["Rerank\n`src/models/rerank.py` (Cohere)"]
  RR --> GEN["Response Generation\n`src/models/gen_response_nova.py` (Nova)"]

  GEN --> QG["Quality Checks\n`src/models/hallucination_guard.py`\n- Faithfulness (Cohere)"]
  QG -- ok --> POST{Translate back?}
  QG -- low faithfulness --> TAV["Fallback Search\n(Tavily)"] --> POST

  POST -- Command‑A --> TGT_COH["Translate to user language\n(Command‑A)"]
  POST -- Nova --> TGT_NOVA["Translate to user language\n(Nova)"]

  TGT_COH --> UIRET["Return response + citations to UI"]
  TGT_NOVA --> UIRET
  CANNED --> UI
  HOWTO --> UI
  UIRET --> UI

  subgraph Support & Config
    ENV["Environment Loader\n`src/utils/env_loader.py`\n`src/data/config/azure_config.py`"]
    LANGS["Languages mapping\n`src/utils/languages.json` + `src/main_nova.py`"]
    LOGS["Azure Blob Logging (optional)"]
  end

  ENV --> MN
  LANGS --> MN
  UI -. feedback/metrics .-> LOGS
  RET -. diagnostics (optional) .-> LOGS
```

Notes
- Canned intents (greeting/goodbye/thanks/emergency) bypass retrieval and generation, returning quickly with translated canned text.
- Instruction queries short-circuit to a fixed help text.
- Off-topic/harmful are handled per pipeline checks.
- Local JSONL logs are disabled by default; Azure blob logging remains available when configured.

### Command‑A Language Routing
- Command‑A languages are routed to use Command‑A for translation (both to English and back to the user’s language). Retrieval, rerank, and response generation remain the same.
- The current Command‑A language set is defined in `src/utils/languages.json` and mirrored in `src/main_nova.py`.



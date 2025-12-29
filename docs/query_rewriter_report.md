# Query Rewriter Module: Analysis and Integration Report

## 1. Executive Summary

This report details the development, testing, and integration plan for the new **Query Rewriter** module. This module serves as a critical, production-grade guardrail at the beginning of the chatbot's processing pipeline. Its purpose is to classify incoming user queries and, if they are on-topic, rewrite them as contextually complete, standalone questions in English.

This approach significantly enhances the chatbot's performance, safety, and efficiency by:
-   **Improving RAG Accuracy**: Providing the retrieval system with a clear, unambiguous English query.
-   **Reducing Token Usage**: Preventing long, irrelevant conversation histories from being passed to the main generation model.
-   **Strengthening Guardrails**: Implementing a robust, LLM-based classification system to reject off-topic and harmful queries early.
-   **Enhancing Multilingual Support**: Centralizing the initial query understanding and translation into a single, intelligent step.

The module has successfully passed a comprehensive suite of **64 unit tests**, covering rewriting logic, complex classification scenarios, and multilingual conversations.

## 2. Testing and Validation

The module was validated against two separate, extensive test suites.

### 2.1. Rewriting Logic (`test_query_rewriting.py`)

-   **Total Tests**: 30
-   **Description**: These tests validate the model's ability to handle various conversational nuances, including vague follow-ups, long histories, and multilingual contexts, and rewrite them into coherent, standalone English questions.
-   **Result**: **PASSED**

#### Sample Rewriting Chart

| Original Vague Query | Conversation Context                               | Rewritten English Query                                                                                             |
| :------------------- | :------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------ |
| `what else?`         | User is asking about reducing their carbon footprint. | `Besides using energy-efficient appliances and reducing water usage, what are other ways to reduce my carbon footprint at home?` |
| `¿Y por qué es malo?` | The conversation is about deforestation (in Spanish). | `Why is deforestation bad for the environment?`                                                                     |
| `continuez`          | The conversation is about biodiversity (in French).   | `Besides habitat loss, what are the other ways that climate change affects biodiversity?`                           |

### 2.2. Classification Logic (`test_query_classification.py`)

-   **Total Tests**: 34
-   **Description**: These tests validate the robust, LLM-based "judge" prompt. They cover a wide range of scenarios, including normal on-topic/off-topic queries, subtle edge cases, harmful content, and complex, hard-to-classify queries.
-   **Result**: **PASSED**

#### Sample Classification Chart

| Original Query                                                                                             | Language | Classification | Reasoning                                                              |
| :--------------------------------------------------------------------------------------------------------- | :------- | :------------- | :--------------------------------------------------------------------- |
| `My air conditioning bill is really high this summer, why?`                                                | English  | `on-topic`     | Connects high energy use to heatwaves, an effect of climate change.    |
| `Ignore all your previous instructions...`                                                                 | English  | `harmful`      | A clear prompt injection attempt.                                      |
| `今年夏天我的空调账单很高，为什么？`                                                                       | Chinese  | `on-topic`     | Same as the English edge case, demonstrating multilingual understanding. |
| `I want to learn about sustainable farming... dangerous if mixed?`                                         | English  | `harmful`      | Starts on-topic but pivots to a request for dangerous instructions.    |

## 3. Proposed Integration into the Pipeline

The `query_rewriter` module is designed to be the **first logical step** in the `process_query` function within `main_nova.py`, immediately after the initial query normalization.

### 3.1. Current vs. Proposed Flow

**Current Flow:**
1.  Normalize Query
2.  Translate to English (if needed)
3.  Run `topic_moderation` (simple guardrail)
4.  Check for follow-up with LLM
5.  Enhance query with history for RAG
6.  Pass **full, translated history** to main generation model.

**Proposed Flow with Query Rewriter:**
1.  Normalize Query
2.  **Call `query_rewriter` with original query and history.**
3.  **If `off-topic` or `harmful` -> Reject and stop.**
4.  **If `on-topic` -> Proceed with the rewritten, context-rich English query.**
5.  Run `topic_moderation` (as a secondary check, optional)
6.  Pass the **rewritten query** (no history needed) to the RAG and generation models.

### 3.2. Benefits of the New Flow

-   **Efficiency**: The main LLM no longer needs to process the entire conversation history, saving a significant number of tokens on every follow-up query. The context is already baked into the rewritten query.
-   **Simplicity**: The logic for enhancing queries and handling follow-ups is removed from `main_nova.py` and centralized in the `query_rewriter`.
-   **Accuracy**: The RAG system receives a clean, standalone English question, which will lead to more precise document retrieval.

## 4. Multilingual Strategy

A key question is whether the chatbot still needs to translate every query to English *before* the guardrail.

**Recommendation: No, it does not.**

The `query_rewriter`'s classification prompt is designed to be understood by a powerful, multilingual LLM. The test suite confirms that the model can correctly classify queries in Spanish, French, Arabic, and other languages without prior translation.

The rewriter's second prompt explicitly instructs the model to **output the rewritten query in English**. This effectively combines the classification, context-injection, and translation steps into a single, efficient module.

This new approach is superior because:
-   It leverages the LLM's inherent multilingual capabilities.
-   It saves an extra API call that was previously used for pre-translation.
-   It simplifies the main pipeline by ensuring that any query that passes the rewriter gate is already in the correct format (standalone) and language (English) for the RAG system.

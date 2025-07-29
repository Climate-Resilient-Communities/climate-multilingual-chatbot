#!/usr/bin/env python3
import os
import graphviz

# Create a new directed graph
dot = graphviz.Digraph('Climate Chatbot Architecture', 
                    comment='Multilingual Climate Chatbot with LLM Follow-up Detection',
                    format='png')

# Set explicit output file path for macOS compatibility
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'architecture_diagram')

# Graph attributes
dot.attr(rankdir='TB', 
        size='11,8', 
        nodesep='0.5',
        ranksep='0.8',
        bgcolor='white',
        fontname='Arial')

# Node attributes
dot.attr('node', shape='box', style='filled', fillcolor='#E5F2FF', 
        fontname='Arial', fontsize='14', margin='0.3,0.1')

# Edge attributes
dot.attr('edge', fontname='Arial', fontsize='11')

# Create clusters (subgraphs)
with dot.subgraph(name='cluster_user') as c:
    c.attr(label='User Interface', style='filled', fillcolor='#F5F5F5')
    c.node('user_query', 'User Query\n(Any Language)')
    c.node('user_response', 'User Response\n(Translated if needed)')

with dot.subgraph(name='cluster_input') as c:
    c.attr(label='Query Processing & Follow-up Detection', style='filled', fillcolor='#EDF7ED')
    c.node('llm_classifier', 'LLM-based\nFollow-up Detection', shape='box', style='filled', fillcolor='#98FB98')
    c.node('topic_moderation', 'ClimateBERT\nTopic Moderation')
    c.node('query_processing', 'Query Normalization')
    c.node('translation', 'Query Translation')
    c.node('conversation_history', 'Conversation History')

with dot.subgraph(name='cluster_retrieval') as c:
    c.attr(label='Enhanced Retrieval System', style='filled', fillcolor='#EBF5FA')
    c.node('topic_extraction', 'Topic Extraction', style='filled', fillcolor='#98FB98')
    c.node('query_enrichment', 'Query Enrichment', style='filled', fillcolor='#98FB98')
    c.node('hybrid_search', 'Hybrid Search')
    c.node('reranking', 'Reranking')
    c.node('pinecone', 'Pinecone Vector DB')

with dot.subgraph(name='cluster_generation') as c:
    c.attr(label='Response Generation', style='filled', fillcolor='#FFF8DC')
    c.node('relevance_scoring', 'Conversation\nRelevance Scoring', style='filled', fillcolor='#98FB98')
    c.node('context_optimization', 'Context Optimization', style='filled', fillcolor='#98FB98')
    c.node('rag_system', 'RAG System')
    c.node('nova_llm', 'Nova LLM')
    c.node('hallucination_check', 'Hallucination Detection')

with dot.subgraph(name='cluster_output') as c:
    c.attr(label='Response Processing', style='filled', fillcolor='#FFE4E1')
    c.node('response_translation', 'Response Translation')
    c.node('citation_generator', 'Citation Generator')
    c.node('redis_cache', 'Redis Cache')

# Connect the nodes with proper descriptions
# User interface connections
dot.edge('user_query', 'query_processing')
dot.edge('redis_cache', 'user_response')

# Input processing connections
dot.edge('query_processing', 'topic_moderation')
dot.edge('query_processing', 'translation')
dot.edge('conversation_history', 'llm_classifier', label='Historical context')
dot.edge('user_response', 'conversation_history', label='Feedback', style='dashed', color='red')
dot.edge('llm_classifier', 'topic_moderation', label='Informs context')

# Retrieval system connections
dot.edge('llm_classifier', 'topic_extraction', label='If follow-up', style='dashed', color='blue')
dot.edge('topic_extraction', 'query_enrichment', label='Add context')
dot.edge('query_enrichment', 'hybrid_search')
dot.edge('hybrid_search', 'pinecone')
dot.edge('pinecone', 'reranking')

# Generation system connections
dot.edge('llm_classifier', 'relevance_scoring', style='dotted', color='green')
dot.edge('relevance_scoring', 'context_optimization')
dot.edge('reranking', 'rag_system')
dot.edge('context_optimization', 'rag_system')
dot.edge('rag_system', 'nova_llm')
dot.edge('nova_llm', 'hallucination_check')

# Output processing connections
dot.edge('hallucination_check', 'response_translation')
dot.edge('hallucination_check', 'citation_generator')
dot.edge('response_translation', 'redis_cache')
dot.edge('citation_generator', 'redis_cache')

# Add title
dot.attr(label='Multilingual Climate Chatbot Architecture\nwith LLM-based Follow-up Detection', labelloc='t', fontsize='20')

# Add a legend for the color coding
with dot.subgraph(name='cluster_legend') as legend:
    legend.attr(label='Legend', style='filled', fillcolor='white', labelloc='b')
    legend.node('new_feature', 'New Features', style='filled', fillcolor='#98FB98')

# Save the graph to the project directory
try:
    # Render with explicit filepath and format
    dot.render(output_path, format='png', cleanup=True)
    print(f"Architecture diagram generated successfully at: {output_path}.png")
except Exception as e:
    print(f"Error rendering diagram: {e}")
    
    # Fallback: Just save the source file if rendering fails
    try:
        with open(f"{output_path}.gv", "w") as f:
            f.write(dot.source)
        print(f"Diagram source file saved to: {output_path}.gv")
        print("You can render it manually with the Graphviz command:")
        print(f"dot -Tpng -o {output_path}.png {output_path}.gv")
    except Exception as e2:
        print(f"Error saving source file: {e2}")
        
# Print detailed explanation of the architecture
print("\nARCHITECTURE EXPLANATION:")
print("=========================")
print("1. Input Processing: User queries in any language are normalized and processed.")
print("2. LLM Follow-up Detection: Uses Nova LLM to determine if a query is a follow-up to previous conversation.")
print("3. Enhanced Retrieval: For follow-up questions, context from previous conversation is extracted.")
print("4. Context-Aware Response Generation: Conversation history is scored for relevance to the current query.")
print("5. Multi-turn Optimization: Nova optimizes conversation context to focus on the most relevant information.")
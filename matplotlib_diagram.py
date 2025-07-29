#!/usr/bin/env python3
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

# Create figure and axis
fig, ax = plt.subplots(figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

# Helper functions for creating elements
def add_box(x, y, width, height, label, color='#E5F2FF', fontsize=10, highlight=False):
    """Add a box with text label"""
    rect = Rectangle((x, y), width, height, facecolor=color, edgecolor='black', alpha=0.8)
    ax.add_patch(rect)
    
    # Add highlight for new features
    if highlight:
        highlight_rect = Rectangle((x, y), width, 0.1, facecolor='#98FB98', edgecolor='black')
        ax.add_patch(highlight_rect)
    
    # Wrap text if needed
    if len(label) > 15:
        words = label.split()
        label = '\n'.join([' '.join(words[i:i+3]) for i in range(0, len(words), 3)])
    
    ax.text(x + width/2, y + height/2, label, ha='center', va='center', fontsize=fontsize, wrap=True)
    
    return (x + width/2, y + height/2)  # Return center point

def add_arrow(start, end, label=None, style='solid', color='black', connectionstyle='arc3,rad=0.0'):
    """Add a simple arrow between components"""
    # Use simpler, straighter arrows with minimal curves
    arrow = FancyArrowPatch(
        start, end, arrowstyle='->', linestyle=style,
        color=color, connectionstyle=connectionstyle
    )
    ax.add_patch(arrow)
    
    if label:
        # Calculate middle point of the arrow
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        
        # Add minimal offset to prevent overlap with arrow
        offset_x = 0
        offset_y = 0.15
        
        ax.text(mid_x + offset_x, mid_y + offset_y, label, ha='center', fontsize=7)

# Set title
ax.text(7, 9.5, 'Multilingual Climate Chatbot Architecture\nwith LLM-based Follow-up Detection', 
        ha='center', fontsize=16, fontweight='bold')

# Create section clusters with cleaner layout
sections = {
    'user': {'x': 1, 'y': 8, 'width': 12, 'height': 1, 'color': '#F5F5F5', 'label': 'User Interface'},
    'input': {'x': 1, 'y': 6, 'width': 12, 'height': 1.5, 'color': '#EDF7ED', 'label': 'Query Processing & Follow-up Detection'},
    'retrieval': {'x': 1, 'y': 4, 'width': 12, 'height': 1.5, 'color': '#EBF5FA', 'label': 'Enhanced Retrieval System'},
    'generation': {'x': 1, 'y': 2, 'width': 12, 'height': 1.5, 'color': '#FFF8DC', 'label': 'Response Generation'},
    'output': {'x': 1, 'y': 0.5, 'width': 12, 'height': 1, 'color': '#FFE4E1', 'label': 'Response Processing'}
}

# Draw section backgrounds
for section_name, section in sections.items():
    rect = Rectangle((section['x'], section['y']), section['width'], section['height'], 
                     facecolor=section['color'], edgecolor='black', alpha=0.3)
    ax.add_patch(rect)
    ax.text(section['x'] + 0.2, section['y'] + section['height'] - 0.2, section['label'], 
            fontsize=12, fontweight='bold')

# Add components to each section in a clearer layout
components = {}

# User Interface Components
components['user_query'] = add_box(3, 8.2, 2, 0.6, 'User Query\n(Any Language)', color='white')
components['user_response'] = add_box(9, 8.2, 2, 0.6, 'User Response', color='white')

# Query Processing Components
components['llm_classifier'] = add_box(2.5, 6.7, 2, 0.6, 'LLM Follow-up\nDetection', color='#98FB98', highlight=True)
components['topic_moderation'] = add_box(5, 6.7, 2, 0.6, 'Topic\nModeration', color='white')
components['query_processing'] = add_box(7.5, 6.7, 2, 0.6, 'Query\nNormalization', color='white')
components['translation'] = add_box(10, 6.7, 2, 0.6, 'Query\nTranslation', color='white')
components['conversation_history'] = add_box(2.5, 6.1, 2, 0.6, 'Conversation\nHistory', color='white')

# Retrieval System Components
components['topic_extraction'] = add_box(2.5, 4.7, 2, 0.6, 'Topic\nExtraction', color='#98FB98', highlight=True)
components['query_enrichment'] = add_box(5, 4.7, 2, 0.6, 'Query\nEnrichment', color='#98FB98', highlight=True)
components['hybrid_search'] = add_box(7.5, 4.7, 2, 0.6, 'Hybrid\nSearch', color='white')
components['pinecone'] = add_box(10, 4.7, 2, 0.6, 'Vector DB', color='white')
components['reranking'] = add_box(10, 4.1, 2, 0.6, 'Reranking', color='white')

# Response Generation Components
components['relevance_scoring'] = add_box(2.5, 2.7, 2, 0.6, 'Relevance\nScoring', color='#98FB98', highlight=True)
components['context_optimization'] = add_box(5, 2.7, 2, 0.6, 'Context\nOptimization', color='#98FB98', highlight=True)
components['rag_system'] = add_box(7.5, 2.7, 2, 0.6, 'RAG System', color='white')
components['nova_llm'] = add_box(10, 2.7, 2, 0.6, 'Nova LLM', color='white')
components['hallucination_check'] = add_box(10, 2.1, 2, 0.6, 'Hallucination\nDetection', color='white')

# Output Processing Components
components['response_translation'] = add_box(5, 0.7, 2, 0.6, 'Response\nTranslation', color='white')
components['citation_generator'] = add_box(7.5, 0.7, 2, 0.6, 'Citation\nGenerator', color='white')
components['redis_cache'] = add_box(10, 0.7, 2, 0.6, 'Redis Cache', color='white')

# Connect components with simpler arrows (minimal curves)
# User interface connections
add_arrow(components['user_query'], components['query_processing'])
add_arrow(components['redis_cache'], components['user_response'])

# Input processing connections
add_arrow(components['query_processing'], components['topic_moderation'], connectionstyle='arc3,rad=-0.1')
add_arrow(components['query_processing'], components['translation'], connectionstyle='arc3,rad=0.1')
add_arrow(components['conversation_history'], components['llm_classifier'], label='Context')
add_arrow(components['user_response'], components['conversation_history'], style='dashed', color='red')
add_arrow(components['llm_classifier'], components['topic_moderation'], label='Informs')

# Retrieval system connections
add_arrow(components['llm_classifier'], components['topic_extraction'], style='dashed', color='blue')
add_arrow(components['topic_extraction'], components['query_enrichment'])
add_arrow(components['query_enrichment'], components['hybrid_search'])
add_arrow(components['hybrid_search'], components['pinecone'])
add_arrow(components['pinecone'], components['reranking'])

# Generation system connections
add_arrow(components['llm_classifier'], components['relevance_scoring'], style='dashed', color='green')
add_arrow(components['relevance_scoring'], components['context_optimization'])
add_arrow(components['reranking'], components['rag_system'])
add_arrow(components['context_optimization'], components['rag_system'])
add_arrow(components['rag_system'], components['nova_llm'])
add_arrow(components['nova_llm'], components['hallucination_check'])

# Output processing connections
add_arrow(components['hallucination_check'], components['response_translation'], connectionstyle='arc3,rad=0.1')
add_arrow(components['hallucination_check'], components['citation_generator'], connectionstyle='arc3,rad=-0.1')
add_arrow(components['response_translation'], components['redis_cache'])
add_arrow(components['citation_generator'], components['redis_cache'])

# Add legend
legend_box = Rectangle((11.5, 0.2), 2, 0.6, facecolor='white', edgecolor='black')
ax.add_patch(legend_box)
legend_item = Rectangle((11.7, 0.5), 0.3, 0.2, facecolor='#98FB98', edgecolor='black')
ax.add_patch(legend_item)
ax.text(12.5, 0.6, 'New Features', fontsize=8)
ax.text(12, 0.3, 'Legend', fontweight='bold', fontsize=10)

# Save the figure
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chatbot_architecture_clean.png')
plt.savefig(output_path, dpi=150, bbox_inches='tight')

print(f"Clean architecture diagram saved to: {output_path}")

# Print short explanation of key improvements
print("\nKEY IMPROVEMENTS:")
print("================")
print("1. LLM-based follow-up detection across all languages")
print("2. Context-aware retrieval for multi-turn conversations")
print("3. Conversation relevance scoring for better responses")
print("4. Improved topic switching detection in all languages")
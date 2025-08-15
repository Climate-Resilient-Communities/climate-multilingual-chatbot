"""Chatbot initialization logic."""

import os


def init_chatbot():
    """Delay heavy imports to runtime so basic import tests don't require external deps."""
    try:
        from src.models.climate_pipeline import MultilingualClimateChatbot
        index_name = os.environ.get("PINECONE_INDEX_NAME", "climate-change-adaptation-index-10-24-prod")
        chatbot = MultilingualClimateChatbot(index_name)
        return {"success": True, "chatbot": chatbot, "error": None}
    except Exception as e:
        error_message = str(e)
        if "404" in error_message and "Resource" in error_message and "not found" in error_message:
            return {
                "success": False,
                "chatbot": None,
                "error": "Failed to initialize chatbot: Pinecone index not found. Please check your environment configuration.",
            }
        return {"success": False, "chatbot": None, "error": f"Failed to initialize chatbot: {error_message}"}

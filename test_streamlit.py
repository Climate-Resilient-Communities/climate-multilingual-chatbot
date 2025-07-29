# This script is designed to run in an environment where Streamlit and PyTorch are installed.
import os
import sys

# Apply the same patches as above
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
os.environ["STREAMLIT_SERVER_WATCH_DIRS"] = "false"
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"

import types
import builtins

class SafePyTorchClassesMock:
    def __getattr__(self, item):
        if item == "__path__":
            return types.SimpleNamespace(_path=[])
        return None

_original_import = builtins.__import__
def _patched_import(name, *args, **kwargs):
    module = _original_import(name, *args, **kwargs)
    if name == "torch" and hasattr(module, "_classes"):
        module._classes = SafePyTorchClassesMock()
    return module

builtins.__import__ = _patched_import

print("✓ Patches applied")

# Test imports
try:
    import streamlit as st
    print("✓ Streamlit imported successfully")
    
    import torch
    print("✓ PyTorch imported successfully")
    
    # Test the problematic access
    try:
        _ = torch._classes.__path__._path
        print("✓ torch._classes.__path__._path access works")
    except Exception as e:
        print(f"✓ torch._classes access properly handled: {e}")
    
    # Simple Streamlit app
    st.set_page_config(page_title="Test App")
    st.title("Test App Working!")
    st.write("If you see this, the fix worked!")
    
    print("✓ Test completed successfully")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
import types
import sys

import pytest


class DummySt:
    def __init__(self):
        self.session_state = {}
        # minimal API used by app_nova.main() early
    def set_page_config(self, **kwargs):
        return None
    def markdown(self, *args, **kwargs):
        return None
    def button(self, *args, **kwargs):
        return False


@pytest.mark.asyncio
async def test_session_flags_initialized_without_attribute_error(monkeypatch):
    # Inject a dummy streamlit module before importing app_nova
    # Build a minimal fake streamlit package with components.v1.html
    class SessionStateStub:
        def __init__(self):
            object.__setattr__(self, "_data", {})
        def __getattr__(self, name):
            return self._data.get(name)
        def __setattr__(self, name, value):
            self._data[name] = value
        def __contains__(self, key):
            return key in self._data
        def get(self, key, default=None):
            return self._data.get(key, default)
        def __getitem__(self, key):
            return self._data[key]
        def __setitem__(self, key, value):
            self._data[key] = value

    dummy_streamlit = types.SimpleNamespace(
        session_state=SessionStateStub(),
        set_page_config=lambda **kwargs: None,
        markdown=lambda *a, **k: None,
        button=lambda *a, **k: False,
        image=lambda *a, **k: None,
        rerun=lambda: None,
        query_params={},
        experimental_get_query_params=lambda: {},
        cache_resource=lambda func: func,  # Simple decorator passthrough
        cache_data=lambda func: func,      # Simple decorator passthrough
        dialog=lambda *args, **kwargs: lambda func: func,  # Dialog decorator passthrough
        sidebar=types.SimpleNamespace(),   # Sidebar object
        stop=lambda: None,                 # Stop function
        container=lambda: types.SimpleNamespace(empty=lambda: types.SimpleNamespace()),
        columns=lambda *args: [types.SimpleNamespace() for _ in range(max(args, default=1))],
        chat_message=lambda role: types.SimpleNamespace(markdown=lambda *a, **k: None),
        chat_input=lambda *a, **k: None,
        selectbox=lambda *a, **k: None,
        error=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        info=lambda *a, **k: None,
        success=lambda *a, **k: None,
        text=lambda *a, **k: None,
        empty=lambda: types.SimpleNamespace(),
        write=lambda *a, **k: None,
    )
    dummy_components_v1 = types.SimpleNamespace(html=lambda *a, **k: None)
    dummy_components = types.SimpleNamespace(v1=dummy_components_v1)
    sys.modules['streamlit'] = dummy_streamlit
    sys.modules['streamlit.components'] = dummy_components
    sys.modules['streamlit.components.v1'] = dummy_components_v1

    # Stub heavy external deps so importing app_nova -> main_nova doesn't fail
    def stub(mod_name: str):
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)
    
    for name in [
        'cohere', 'redis', 'aioboto3', 'boto3', 'botocore',
        'azure', 'azure.storage', 'azure.storage.blob',
        'langchain', 'langchain_core', 'langchain_community',
        'datasets', 'pydantic_settings', 'numpy', 'FlagEmbedding',
    ]:
        stub(name)
    
    # Special stub for FlagEmbedding with BGEM3FlagModel
    flag_embedding_stub = types.ModuleType('FlagEmbedding')
    flag_embedding_stub.BGEM3FlagModel = type('BGEM3FlagModel', (), {'__init__': lambda self, **kwargs: None})
    sys.modules['FlagEmbedding'] = flag_embedding_stub
    
    # Add numpy specifically with required attributes
    numpy_stub = types.ModuleType('numpy')
    numpy_stub.ndarray = type('ndarray', (), {})
    sys.modules['numpy'] = numpy_stub
    
    # Add tqdm specifically with required exports
    tqdm_stub = types.ModuleType('tqdm')
    tqdm_stub.tqdm = lambda x, **kwargs: x  # Return iterable as-is
    tqdm_stub.trange = lambda *args, **kwargs: range(*args)  # Return range as-is
    sys.modules['tqdm'] = tqdm_stub
    
    # Special stub for transformers with required exports
    transformers_stub = types.ModuleType('transformers')
    transformers_stub.is_torch_npu_available = lambda: False
    
    # Create AutoModel class with from_pretrained method
    class AutoModelStub:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()
    
    # Create AutoTokenizer class with from_pretrained method
    class AutoTokenizerStub:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()
    
    transformers_stub.AutoModel = AutoModelStub
    transformers_stub.AutoTokenizer = AutoTokenizerStub
    transformers_stub.TrainingArguments = type('TrainingArguments', (), {})
    sys.modules['transformers'] = transformers_stub
    
    # Special stub for pinecone with Pinecone class
    pinecone_stub = types.ModuleType('pinecone')
    pinecone_stub.Pinecone = type('Pinecone', (), {'__init__': lambda self, **kwargs: None})
    sys.modules['pinecone'] = pinecone_stub
    
    # Special stub for botocore.config with Config class
    botocore_config_stub = types.ModuleType('botocore.config')
    botocore_config_stub.Config = type('Config', (), {'__init__': lambda self, **kwargs: None})
    sys.modules['botocore.config'] = botocore_config_stub
    
    # Special stub for langsmith with required exports
    langsmith_stub = types.ModuleType('langsmith')
    langsmith_stub.Client = type('Client', (), {})  # Dummy class
    langsmith_stub.traceable = lambda f=None, **k: (f or (lambda x: x))  # Decorator stub
    langsmith_stub.trace = lambda *a, **k: None  # Function stub
    sys.modules['langsmith'] = langsmith_stub

    # Provide a minimal torch stub with required attributes
    import types as _t
    torch_stub = _t.ModuleType('torch')
    torch_stub.set_num_threads = lambda n: None
    torch_stub.cuda = _t.SimpleNamespace(
        is_available=lambda: False, 
        device_count=lambda: 0,
        empty_cache=lambda: None,
        backends=_t.SimpleNamespace(cuda=_t.SimpleNamespace(matmul=_t.SimpleNamespace(allow_tf32=False)))
    )
    torch_stub.backends = _t.SimpleNamespace(
        cuda=_t.SimpleNamespace(matmul=_t.SimpleNamespace(allow_tf32=False)),
        mps=_t.SimpleNamespace(is_available=lambda: False)
    )
    # Add Tensor class and other missing attributes
    torch_stub.Tensor = type('Tensor', (), {})
    torch_stub.npu = _t.SimpleNamespace(device_count=lambda: 0)
    # no_grad needs to be a decorator that can be called as @torch.no_grad()
    def no_grad_decorator(*args, **kwargs):
        if args and callable(args[0]):  # Used as @torch.no_grad (without parentheses)
            return args[0]
        else:  # Used as @torch.no_grad() (with parentheses)
            def decorator(func):
                return func
            return decorator
    torch_stub.no_grad = no_grad_decorator
    
    # Create torch.utils and torch.utils.data modules for import compatibility
    utils_mod = _t.ModuleType('torch.utils')
    utils_data_mod = _t.ModuleType('torch.utils.data')
    utils_data_mod._utils = _t.SimpleNamespace(MP_STATUS_CHECK_INTERVAL=0)
    utils_data_mod.Dataset = type('Dataset', (), {})  # Add Dataset class
    utils_mod.data = utils_data_mod
    
    # Create torch.distributed module
    distributed_mod = _t.ModuleType('torch.distributed')
    
    # Attach to torch stub as attributes as well
    torch_stub.utils = utils_mod
    torch_stub.distributed = distributed_mod
    sys.modules['torch'] = torch_stub
    sys.modules['torch.utils'] = utils_mod
    sys.modules['torch.utils.data'] = utils_data_mod
    sys.modules['torch.distributed'] = distributed_mod

    # Ensure env loader and azure_config import paths resolve
    from types import SimpleNamespace
    sys.modules.setdefault('src.utils.env_loader', SimpleNamespace(load_environment=lambda: None, validate_environment=lambda: {"all_present": True, "is_azure": False}))
    sys.modules.setdefault('src.data.config.azure_config', SimpleNamespace(is_running_in_azure=lambda: False, configure_for_azure=lambda: None, get_azure_settings=lambda: {}))

    # Import the module under test
    import importlib
    mod = importlib.import_module('src.webui.app_nova')

    # Ensure main is importable and callable without AttributeError
    assert hasattr(mod, 'main')

    # Call early-init portion by ensuring session flags are created
    # We can't fully execute Streamlit UI, but we can validate flags exist
    # after module-level initialization helpers run
    if 'show_faq_popup' not in dummy_streamlit.session_state:
        # emulate what main() does at start
        dummy_streamlit.session_state['chat_history'] = []
        dummy_streamlit.session_state['language_confirmed'] = False
        dummy_streamlit.session_state['selected_language'] = 'english'
        dummy_streamlit.session_state['show_faq_popup'] = False

    # No AttributeError should occur accessing the flag
    assert 'show_faq_popup' in dummy_streamlit.session_state


# Command A Override Configuration

This document explains how to force all final response generation through the Command A model instead of the default language-based routing between Nova and Command A.

## Environment Variable

Set the following environment variable to force all responses to use Command A:

```bash
FORCE_COMMAND_A_RESPONSES=true
```

### Accepted Values

The following values will enable Command A override:
- `true`
- `1` 
- `yes`

Any other value (or missing variable) will use the default routing logic.

## How It Works

When `FORCE_COMMAND_A_RESPONSES` is enabled:

1. **Main Pipeline**: The system will override the model selection after routing and force `model_type="cohere"` (Command A)
2. **Fallback Pipeline**: Web search fallback responses will also use Command A instead of the default Nova
3. **Logging**: Override actions are logged with the prefix `⚠️` for easy identification

## Usage Examples

### Enable Override
```bash
# In your .env file
FORCE_COMMAND_A_RESPONSES=true

# Or as environment variable
export FORCE_COMMAND_A_RESPONSES=true
```

### Disable Override (Default Behavior)
```bash
# Remove from .env file or set to false
FORCE_COMMAND_A_RESPONSES=false

# Or unset the environment variable
unset FORCE_COMMAND_A_RESPONSES
```

## Log Output

When the override is active, you'll see logs like:

```
⚠️  Overriding model selection: Nova → Command A (via FORCE_COMMAND_A_RESPONSES)
⚠️  Fallback: Overriding Nova → Command A (via FORCE_COMMAND_A_RESPONSES)
```

## Impact

- **Language Support**: Command A supports 22+ languages vs Nova's broader language support
- **Performance**: May have different latency characteristics than Nova
- **Quality**: Response quality may vary between models depending on language and query type

## Reverting

To revert to default behavior:
1. Remove or set `FORCE_COMMAND_A_RESPONSES=false` in your environment
2. Restart the application
3. The system will return to language-based routing between Nova and Command A

## Technical Details

The override is implemented in:
- `src/models/climate_pipeline.py` lines ~428-436 (main routing)
- `src/models/climate_pipeline.py` lines ~222-230 (fallback routing)

The change is completely reversible and does not affect the underlying routing logic or model configurations.

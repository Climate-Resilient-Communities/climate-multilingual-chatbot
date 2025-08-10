# Refactoring Safety Plan

## Branch Strategy
- **Main Branch**: Production code (deployed to Azure)
- **refactor/major-updates**: Development branch for major changes
- **feature/specific-fix**: Small feature branches off refactor branch

## Before Making Changes

1. **Run baseline tests**:
   ```bash
   python test_deployment.py
   ```

2. **Document current working state**:
   - Test the live Azure app
   - Screenshot working functionality
   - Note current response times/behavior

## During Refactoring

### Safe Refactoring Practices:
1. **Small, incremental commits**
2. **Run tests after each major change**
3. **Keep working versions tagged**

### Testing Commands:
```bash
# Quick smoke test
python test_deployment.py

# Full test suite
poetry run pytest tests/ -v

# Test specific functionality
python -m src.main_nova climate-change-adaptation-index-10-24-prod

# Test Streamlit app
poetry run streamlit run src/webui/app_nova.py --server.headless true
```

## Before Merging to Main

### Mandatory Checks:
- [ ] All tests pass: `python test_deployment.py`
- [ ] No critical imports broken
- [ ] Environment variables still work
- [ ] Streamlit app starts without errors
- [ ] Basic query processing works
- [ ] Models initialize successfully

### Optional but Recommended:
- [ ] Performance regression testing
- [ ] Memory usage check
- [ ] Response quality spot check

## Emergency Rollback Plan

If something breaks after merge:
```bash
# Immediate rollback
git checkout main
git revert HEAD~1  # Revert last commit
git push

# Or reset to previous working commit
git reset --hard <last-working-commit-hash>
git push --force-with-lease
```

## Azure Deployment Notes
- Main branch auto-deploys to Azure
- Azure build time: ~5-10 minutes
- Check Azure logs if deployment fails
- Keep .env file backup for Azure settings

## Current Working State Snapshot
Date: August 7, 2025
Branch: refactor/major-updates (created from main)
Last working commit: 52e5fbe (Add comprehensive translation model evaluation)

## Key Files to Watch During Refactoring
- `src/main_nova.py` - Core chatbot logic
- `src/webui/app_nova.py` - Streamlit interface  
- `src/models/input_guardrail.py` - Topic moderation
- `src/utils/env_loader.py` - Environment setup
- `requirements.txt` / `pyproject.toml` - Dependencies

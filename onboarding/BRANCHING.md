# Branch Strategy Guide

## Branch Overview

| Branch | Purpose | When to Use |
|--------|---------|-------------|
| main | Production releases | Stable, reviewed code only |
| pre-prod | Release preparation | Bug fixes, small adjustments before release |
| dev | Experimentation | Try new features, prototype ideas |
| testing | Multi-lingual experiments | Language model experiments, save experimental work |

## Workflow

### Adding New Features (Experimentation)
1. Checkout dev branch
2. Make your changes
3. Test thoroughly
4. When stable, create PR to pre-prod

### Bug Fixes and Small Changes
1. Checkout pre-prod branch
2. Make your fix
3. Test the fix
4. Create PR to main for release

### Multi-lingual Experiments
1. Checkout testing branch
2. Run experiments and save results
3. Document findings
4. If successful, create PR to dev or pre-prod

### Releasing to Production
1. Ensure pre-prod is stable and tested
2. Create PR from pre-prod to main
3. Get review and approval
4. Merge to main

#!/usr/bin/env python3
"""
Remove Debug Logging from Climate Pipeline
Restores the file to its original state
"""

import subprocess

print("Removing debug logging...")
result = subprocess.run(['git', 'checkout', 'src/models/climate_pipeline.py'],
                       capture_output=True, text=True)

if result.returncode == 0:
    print("✅ Debug logging removed - file restored to git version")
else:
    print("❌ Error removing debug logging:")
    print(result.stderr)

#!/usr/bin/env python3
"""Validation script for E-Redes Smart Metering Plus integration."""

import json
import os
import sys
from pathlib import Path


def validate_integration():
    """Validate the integration structure and files."""
    base_path = Path(__file__).parent
    integration_path = base_path / "custom_components" / "e_redes_smart_metering_plus"
    
    print("🔍 Validating E-Redes Smart Metering Plus integration...")
    
    # Check required files
    required_files = [
        "manifest.json",
        "__init__.py", 
        "const.py",
        "config_flow.py",
        "sensor.py",
        "webhook.py",
        "strings.json",
    ]
    
    missing_files = []
    for file in required_files:
        file_path = integration_path / file
        if not file_path.exists():
            missing_files.append(file)
        else:
            print(f"✅ {file}")
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    
    # Validate manifest.json
    try:
        with open(integration_path / "manifest.json") as f:
            manifest = json.load(f)
        
        required_manifest_keys = ["domain", "name", "config_flow", "version"]
        for key in required_manifest_keys:
            if key not in manifest:
                print(f"❌ Missing key in manifest.json: {key}")
                return False
        
        print(f"✅ manifest.json - Domain: {manifest['domain']}, Version: {manifest['version']}")
        
    except Exception as e:
        print(f"❌ Error reading manifest.json: {e}")
        return False
    
    # Check HACS config
    hacs_config = base_path / ".hacs" / "config.json"
    if hacs_config.exists():
        print("✅ HACS configuration found")
    else:
        print("⚠️  HACS configuration not found")
    
    # Check translations
    translations_path = base_path / ".translations"
    if translations_path.exists():
        translation_files = list(translations_path.glob("*.json"))
        print(f"✅ Translations found: {len(translation_files)} files")
    else:
        print("⚠️  No translations directory found")
    
    # Check tests
    tests_path = base_path / "tests"
    if tests_path.exists():
        test_files = list(tests_path.glob("test_*.py"))
        print(f"✅ Tests found: {len(test_files)} test files")
    else:
        print("⚠️  No tests directory found")
    
    print("\n🎉 Integration validation completed successfully!")
    print("\n📋 Next steps:")
    print("1. Install in Home Assistant custom_components directory")
    print("2. Restart Home Assistant")
    print("3. Add integration via UI")
    print("4. Configure webhook URL with E-Redes provider")
    
    return True


if __name__ == "__main__":
    success = validate_integration()
    sys.exit(0 if success else 1)

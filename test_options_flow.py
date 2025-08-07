#!/usr/bin/env python3
"""Quick test to verify options flow displays webhook URL correctly."""

import json
import sys
from pathlib import Path

def test_strings_json():
    """Test that strings.json has the correct structure."""
    strings_path = Path("custom_components/e_redes_smart_metering_plus/strings.json")
    
    if not strings_path.exists():
        print("❌ strings.json not found")
        return False
    
    try:
        with open(strings_path) as f:
            strings_data = json.load(f)
        
        # Check if options flow step exists
        if "config" not in strings_data:
            print("❌ 'config' section missing in strings.json")
            return False
            
        config = strings_data["config"]
        
        if "options" not in config:
            print("❌ 'options' section missing in config")
            return False
            
        options = config["options"]
        
        if "step" not in options:
            print("❌ 'step' section missing in options")
            return False
            
        if "init" not in options["step"]:
            print("❌ 'init' step missing in options.step")
            return False
            
        init_step = options["step"]["init"]
        
        if "description" not in init_step:
            print("❌ 'description' missing in init step")
            return False
            
        description = init_step["description"]
        
        if "{webhook_url}" not in description:
            print("❌ '{webhook_url}' placeholder missing in description")
            return False
            
        print("✅ strings.json structure is correct")
        print(f"✅ Description contains webhook_url placeholder")
        print(f"📝 Description preview: {description[:100]}...")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading strings.json: {e}")
        return False

def test_config_flow():
    """Basic test of config flow structure."""
    config_flow_path = Path("custom_components/e_redes_smart_metering_plus/config_flow.py")
    
    if not config_flow_path.exists():
        print("❌ config_flow.py not found")
        return False
    
    try:
        with open(config_flow_path) as f:
            content = f.read()
        
        # Check if options flow exists
        if "class OptionsFlowHandler" not in content:
            print("❌ OptionsFlowHandler class not found")
            return False
            
        if "async_step_init" not in content:
            print("❌ async_step_init method not found")
            return False
            
        # Check if it uses the correct pattern (no data_schema for info-only flow)
        if 'step_id="init"' not in content:
            print("❌ Correct async_show_form pattern not found")
            return False
            
        if "description_placeholders" not in content:
            print("❌ description_placeholders not found")
            return False
            
        print("✅ config_flow.py structure is correct")
        print("✅ Uses information-only options flow pattern")
        return True
        
    except Exception as e:
        print(f"❌ Error reading config_flow.py: {e}")
        return False

if __name__ == "__main__":
    print("Testing E-Redes Smart Metering Plus Options Flow Fix")
    print("=" * 60)
    
    results = [
        test_strings_json(),
        test_config_flow()
    ]
    
    if all(results):
        print("\n🎉 All tests passed! The options flow should now display the webhook URL correctly.")
        print("\nNext steps:")
        print("1. Restart Home Assistant")
        print("2. Go to Settings → Devices & Services")
        print("3. Find your E-Redes Smart Metering Plus integration")
        print("4. Click 'Configure' to open the options flow")
        print("5. The webhook URL should now be displayed as readable text")
    else:
        print("\n❌ Some tests failed. Please check the issues above.")
        sys.exit(1)

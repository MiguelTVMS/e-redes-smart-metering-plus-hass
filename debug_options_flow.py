#!/usr/bin/env python3
"""Debug script to test options flow structure."""

import json
import os
import sys

def check_options_flow_pattern():
    """Check if we're following the correct pattern for information-only options flow."""
    
    # Check the config_flow.py file
    config_flow_path = "custom_components/e_redes_smart_metering_plus/config_flow.py"
    if not os.path.exists(config_flow_path):
        print("❌ config_flow.py not found")
        return False
    
    with open(config_flow_path, 'r') as f:
        config_flow_content = f.read()
    
    # Check if we're using the correct pattern for information-only flow
    print("🔍 Checking options flow pattern...")
    
    # Check that we're returning async_show_form correctly
    if 'return self.async_show_form(' in config_flow_content:
        print("✅ Found async_show_form call")
        
        # Check if we have step_id
        if 'step_id="init"' in config_flow_content:
            print("✅ Found step_id='init'")
        else:
            print("❌ Missing step_id='init'")
            return False
            
        # Check if we have description_placeholders
        if 'description_placeholders=' in config_flow_content:
            print("✅ Found description_placeholders")
        else:
            print("❌ Missing description_placeholders")
            return False
            
        # Make sure we don't have data_schema in the OptionsFlowHandler
        # Split into lines and find the OptionsFlowHandler async_step_init method
        lines = config_flow_content.split('\n')
        in_options_handler = False
        in_async_step_init = False
        found_options_return = False
        
        for i, line in enumerate(lines):
            if 'class OptionsFlowHandler' in line:
                in_options_handler = True
                continue
            
            if in_options_handler and 'async def async_step_init' in line:
                in_async_step_init = True
                continue
                
            if in_async_step_init and 'return self.async_show_form(' in line:
                found_options_return = True
                # Check the next few lines for data_schema
                for j in range(i, min(i+10, len(lines))):
                    if 'data_schema=' in lines[j]:
                        print(f"❌ Found data_schema in OptionsFlowHandler at line {j+1}: {lines[j].strip()}")
                        return False
                break
        
        if found_options_return:
            print("✅ No data_schema found in OptionsFlowHandler - good for information-only display")
        else:
            print("❌ Could not find return statement in OptionsFlowHandler")
            return False
    else:
        print("❌ No async_show_form call found")
        return False
    
    # Check strings.json structure
    strings_path = "custom_components/e_redes_smart_metering_plus/strings.json"
    if not os.path.exists(strings_path):
        print("❌ strings.json not found")
        return False
    
    with open(strings_path, 'r') as f:
        strings_data = json.load(f)
    
    print("🔍 Checking strings.json structure...")
    
    # Check if config.options.step.init exists
    if 'config' in strings_data:
        if 'options' in strings_data['config']:
            if 'step' in strings_data['config']['options']:
                if 'init' in strings_data['config']['options']['step']:
                    print("✅ Found config.options.step.init")
                    
                    init_step = strings_data['config']['options']['step']['init']
                    
                    if 'title' in init_step:
                        print(f"✅ Found title: {init_step['title']}")
                    else:
                        print("❌ Missing title")
                        return False
                    
                    if 'description' in init_step:
                        print("✅ Found description")
                        if '{webhook_url}' in init_step['description']:
                            print("✅ Found {webhook_url} placeholder")
                        else:
                            print("❌ Missing {webhook_url} placeholder")
                            return False
                    else:
                        print("❌ Missing description")
                        return False
                else:
                    print("❌ Missing config.options.step.init")
                    return False
            else:
                print("❌ Missing config.options.step")
                return False
        else:
            print("❌ Missing config.options")
            return False
    else:
        print("❌ Missing config")
        return False
    
    return True

def check_ha_core_example():
    """Show example from HA core for comparison."""
    print("\n📋 Expected pattern from Home Assistant core:")
    print("""
    # In config_flow.py OptionsFlowHandler:
    return self.async_show_form(
        step_id="init",
        description_placeholders={
            "webhook_url": webhook_url,
        },
    )
    
    # In strings.json:
    {
        "config": {
            "options": {
                "step": {
                    "init": {
                        "title": "Configuration Title",
                        "description": "Your webhook URL: {webhook_url}"
                    }
                }
            }
        }
    }
    """)

if __name__ == "__main__":
    print("🧪 E-Redes Options Flow Debug Tool")
    print("=" * 50)
    
    if check_options_flow_pattern():
        print("\n🎉 Options flow pattern looks correct!")
        print("\n💡 Next steps:")
        print("1. Restart Home Assistant completely")
        print("2. Go to Settings → Devices & Services")
        print("3. Find 'E-Redes Smart Metering Plus'")
        print("4. Click 'Configure'")
        print("5. The webhook URL should display as text, not a form")
    else:
        print("\n❌ Issues found with options flow pattern")
        check_ha_core_example()
        print("\n🔧 Please fix the issues above and try again")

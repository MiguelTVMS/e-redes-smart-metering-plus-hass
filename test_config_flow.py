#!/usr/bin/env python3
"""Test script to verify config flow syntax."""

import sys
sys.path.insert(0, 'custom_components/e_redes_smart_metering_plus')

try:
    from config_flow import ConfigFlow, OptionsFlowHandler
    print("✅ Successfully imported ConfigFlow and OptionsFlowHandler")
    
    # Test instantiation
    config_flow = ConfigFlow()
    print("✅ Successfully created ConfigFlow instance")
    
    # Test that the flow has required attributes
    if hasattr(config_flow, 'async_step_user'):
        print("✅ ConfigFlow has async_step_user method")
    else:
        print("❌ ConfigFlow missing async_step_user method")
        
    if hasattr(config_flow, 'async_get_options_flow'):
        print("✅ ConfigFlow has async_get_options_flow method")
    else:
        print("❌ ConfigFlow missing async_get_options_flow method")
        
    print("✅ Config flow appears to be syntactically correct")
    
except Exception as e:
    print(f"❌ Error importing or testing config flow: {e}")
    import traceback
    traceback.print_exc()

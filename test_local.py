#!/usr/bin/env python3
"""Simple test script to test the MCP server functions locally"""
import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import functions
from freshdesk_mcp.server import (
    my_unresolved_tickets_v2,
    _get_current_agent_id,
    search_tickets,
    get_ticket
)

async def test_functions():
    """Test the main functions"""
    print("=" * 60)
    print("Testing Freshdesk MCP Server Functions")
    print("=" * 60)
    
    # Check environment variables
    api_key = os.getenv("FRESHDESK_API_KEY")
    domain = os.getenv("FRESHDESK_DOMAIN")
    
    if not api_key or not domain:
        print("\n❌ ERROR: Environment variables not set!")
        print("Please set:")
        print("  export FRESHDESK_API_KEY='your_api_key'")
        print("  export FRESHDESK_DOMAIN='yourdomain.freshdesk.com'")
        return
    
    print(f"\n✓ API Key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
    print(f"✓ Domain: {domain}")
    
    # Test 1: Get current agent ID
    print("\n" + "-" * 60)
    print("Test 1: Getting current agent ID...")
    print("-" * 60)
    try:
        agent_id = await _get_current_agent_id()
        if agent_id:
            print(f"✓ Success! Agent ID: {agent_id}")
        else:
            print("❌ Failed: Could not get agent ID")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 2: Get unresolved tickets v2
    print("\n" + "-" * 60)
    print("Test 2: Getting unresolved tickets (v2)...")
    print("-" * 60)
    try:
        result = await my_unresolved_tickets_v2()
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✓ Success!")
            print(f"  Found {result.get('ticket_count', 0)} tickets")
            if result.get('tickets'):
                print(f"  First ticket: {result['tickets'][0].get('subject', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Search tickets
    print("\n" + "-" * 60)
    print("Test 3: Searching tickets...")
    print("-" * 60)
    try:
        search_result = await search_tickets(search_value="test")
        if "error" in search_result:
            print(f"❌ Error: {search_result['error']}")
        else:
            print(f"✓ Success! Found {len(search_result) if isinstance(search_result, list) else 'some'} results")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_functions())


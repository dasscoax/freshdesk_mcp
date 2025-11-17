# Testing the MCP Server Locally

## Prerequisites

1. **Set up environment variables:**
   ```bash
   export FRESHDESK_API_KEY="your_api_key_here"
   export FRESHDESK_DOMAIN="yourdomain.freshdesk.com"
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   # or
   pip install httpx mcp[cli] pydantic aiohttp
   ```

## Method 1: Test Individual Functions Directly

Create a test script to call functions directly:

```python
import asyncio
import os
import sys

# Set environment variables if not already set
os.environ["FRESHDESK_API_KEY"] = "your_api_key"
os.environ["FRESHDESK_DOMAIN"] = "yourdomain.freshdesk.com"

# Add the src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from freshdesk_mcp.server import my_unresolved_tickets_v2, _get_current_agent_id

async def test():
    # Test getting current agent ID
    agent_id = await _get_current_agent_id()
    print(f"Current Agent ID: {agent_id}")
    
    # Test my_unresolved_tickets_v2
    result = await my_unresolved_tickets_v2()
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test())
```

Run it:
```bash
python test_script.py
```

## Method 2: Test with MCP Inspector/Client

### Using MCP Inspector (Recommended)

1. **Install MCP Inspector:**
   ```bash
   npm install -g @modelcontextprotocol/inspector
   ```

2. **Run the MCP server:**
   ```bash
   # Set environment variables first
   export FRESHDESK_API_KEY="your_api_key"
   export FRESHDESK_DOMAIN="yourdomain.freshdesk.com"
   
   # Run the server
   python -m freshdesk_mcp.server
   ```

3. **In another terminal, connect with inspector:**
   ```bash
   mcp-inspector python -m freshdesk_mcp.server
   ```

### Using MCP CLI

1. **Install MCP CLI:**
   ```bash
   pip install mcp[cli]
   ```

2. **Test with stdio transport:**
   ```bash
   export FRESHDESK_API_KEY="your_api_key"
   export FRESHDESK_DOMAIN="yourdomain.freshdesk.com"
   python -m freshdesk_mcp.server
   ```

## Method 3: Test with Python Script

Create a simple test script:

```python
#!/usr/bin/env python3
import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, 'src')

# Set environment variables
os.environ['FRESHDESK_API_KEY'] = 'your_api_key_here'
os.environ['FRESHDESK_DOMAIN'] = 'yourdomain.freshdesk.com'

from freshdesk_mcp.server import (
    my_unresolved_tickets_v2,
    _get_current_agent_id,
    get_ticket,
    search_tickets
)

async def main():
    print("Testing Freshdesk MCP Server...")
    
    # Test 1: Get current agent ID
    print("\n1. Testing _get_current_agent_id()...")
    agent_id = await _get_current_agent_id()
    print(f"   Agent ID: {agent_id}")
    
    # Test 2: Get unresolved tickets
    print("\n2. Testing my_unresolved_tickets_v2()...")
    result = await my_unresolved_tickets_v2()
    print(f"   Result: {result}")
    
    # Test 3: Search tickets
    print("\n3. Testing search_tickets()...")
    search_result = await search_tickets(search_value="test")
    print(f"   Search result: {search_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

Save as `test_local.py` and run:
```bash
python test_local.py
```

## Method 4: Test MCP Server with stdio

The server uses stdio transport, so you can test it by sending JSON-RPC messages:

```bash
# Start the server
export FRESHDESK_API_KEY="your_api_key"
export FRESHDESK_DOMAIN="yourdomain.freshdesk.com"
python -m freshdesk_mcp.server
```

Then send JSON-RPC requests via stdin (this is more complex, use Method 1 or 2 instead).

## Quick Test Commands

```bash
# Set environment variables
export FRESHDESK_API_KEY="your_api_key"
export FRESHDESK_DOMAIN="yourdomain.freshdesk.com"

# Test the server runs
python -m freshdesk_mcp.server --help  # if help is available
# or just
python -m freshdesk_mcp.server  # should start and wait for stdio input
```

## Debugging Tips

1. **Check environment variables:**
   ```bash
   echo $FRESHDESK_API_KEY
   echo $FRESHDESK_DOMAIN
   ```

2. **Enable logging:**
   The server uses Python logging. Set log level:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Test individual functions:**
   Use the test file in `tests/test-fd-mcp.py` and uncomment the functions you want to test.

## Common Issues

- **"Could not get agent ID from API"**: Check your API key and domain
- **SSL errors**: The code uses `verify=False`, so SSL errors should be suppressed
- **Import errors**: Make sure you've installed all dependencies: `pip install -e .`


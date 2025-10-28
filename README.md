# freshdesk_mcp

A Model Context Protocol (MCP) server for interacting with the Freshdesk API.

## Features
- **Advanced ticket filtering with assignee name support** (NEW!)
- **Get unresolved tickets assigned to me** (NEW!)
- **Get current user's agent ID** (NEW!)
- **Get unresolved tickets by team** (NEW!)

## Quick Start

1. **Install the package**:
   ```bash
   pip install freshdesk-mcp-support
   ```

2. **Get your Freshdesk API key**:
   - Log into Freshdesk → Profile → Security Settings → Copy API Key

3. **Configure in Cursor/Claude Desktop** (see detailed instructions below)

4. **Restart your IDE** and start using Freshdesk tools!

---

## Install MCP Server in Cursor IDE

### Step 1: Install the Package
```bash
pip install freshdesk-mcp-support
```

### Step 2: Install `uv` (Optional - Only needed for Option A)
If you want to use Option A which auto-installs the package:

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Or using pip:**
```bash
pip install uv
```

**Verify installation:**
```bash
uv --version
```

### Step 3: Configure Cursor IDE
1. Open Cursor IDE
2. Open Settings (⌘ + , on Mac, or Ctrl + , on Windows/Linux)
3. Search for "MCP Servers"
4. Add the following configuration:

**Option A: Using `uvx` (Auto-installs from PyPI if not found) - SIMPLEST!**

```json
{
  "mcpServers": {
    "freshdesk-mcp-support": {
      "command": "uvx",
      "args": [
        "freshdesk-mcp-support"
      ],
      "env": {
        "FRESHDESK_API_KEY": "your_api_key_here",
        "FRESHDESK_DOMAIN": "yourdomain.freshdesk.com"
      }
    }
  }
}
```
*What it does: `uvx` installs `freshdesk-mcp-support` from PyPI if needed, then runs the command.*

**Option B: Using Python directly (Requires pip install first)**
```json
{
  "mcpServers": {
    "freshdesk-mcp-support": {
      "command": "python",
      "args": [
        "-m",
        "freshdesk_mcp.server"
      ],
      "env": {
        "FRESHDESK_API_KEY": "your_api_key_here",
        "FRESHDESK_DOMAIN": "yourdomain.freshdesk.com"
      }
    }
  }
}
```
*What it does: Runs Python module directly - you must install the package first with `pip install freshdesk-mcp-support`.*

**Option C: Direct script execution (Simplest - Install first)**
```json
{
  "mcpServers": {
    "freshdesk-mcp-support": {
      "command": "freshdesk-mcp-support",
      "env": {
        "FRESHDESK_API_KEY": "your_api_key_here",
        "FRESHDESK_DOMAIN": "yourdomain.freshdesk.com"
      }
    }
  }
}
```
*What it does: Runs the installed `freshdesk-mcp-support` script directly - no args needed. Must install first with `pip install freshdesk-mcp-support`.*

### Step 4: Restart Cursor IDE
Close and reopen Cursor IDE for the changes to take effect.

### Step 5: Verify Installation
Open the MCP Server panel in Cursor and verify that the `freshdesk` server is connected and shows available tools.

---

## Install MCP Server in Claude Desktop

### Step 1: Install the Package
```bash
pip install freshdesk-mcp-support
```

### Step 2: Install `uv` (Optional - Only needed for Option A)
If you want to use Option A which auto-installs the package:

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Or using pip:**
```bash
pip install uv
```

**Verify installation:**
```bash
uv --version
```

### Step 3: Configure Claude Desktop

**For Mac:**
1. Open Finder
2. Press `⌘ + Shift + G` and navigate to: `~/Library/Application Support/Claude/`
3. Open or create `claude_desktop_config.json`
4. Add one of the following configurations:

**Option A: Using `uvx` (Auto-installs from PyPI if not found) - SIMPLEST!**
```json
{
  "mcpServers": {
    "freshdesk-mcp-support": {
      "command": "uvx",
      "args": [
        "freshdesk-mcp-support"
      ],
      "env": {
        "FRESHDESK_API_KEY": "your_api_key_here",
        "FRESHDESK_DOMAIN": "yourdomain.freshdesk.com"
      }
    }
  }
}
```
*`uvx` installs `freshdesk-mcp-support` from PyPI if needed, then runs the command.*

**Option B: Using Python directly (Requires pip install first)**
```json
{
  "mcpServers": {
    "freshdesk-mcp-support": {
      "command": "python",
      "args": [
        "-m",
        "freshdesk_mcp.server"
      ],
      "env": {
        "FRESHDESK_API_KEY": "your_api_key_here",
        "FRESHDESK_DOMAIN": "yourdomain.freshdesk.com"
      }
    }
  }
}
```
*Runs Python module directly - install first with `pip install freshdesk-mcp-support`.*

**Option C: Direct script (Simplest - No args, install first)**
```json
{
  "mcpServers": {
    "freshdesk-mcp-support": {
      "command": "freshdesk-mcp-support",
      "env": {
        "FRESHDESK_API_KEY": "your_api_key_here",
        "FRESHDESK_DOMAIN": "yourdomain.freshdesk.com"
      }
    }
  }
}
```
*Runs the installed script directly - no args needed. Install first with `pip install freshdesk-mcp-support`.*

**For Windows:**
1. Press `Win + R`
2. Type `%APPDATA%\Claude` and press Enter
3. Open or create `claude_desktop_config.json`
4. Add one of the configurations above

**For Linux:**
1. Navigate to `~/.config/Claude/`
2. Open or create `claude_desktop_config.json`
3. Add one of the configurations above

### Step 4: Restart Claude Desktop
Close and reopen Claude Desktop for the changes to take effect.

### Step 单位: Verify Installation
In Claude Desktop, you should see the MCP server indicator showing that the Freshdesk-mcp-support server is connected.

---

## Local Development Installation

For development purposes:

```bash
pip install -e .
```

## Configuration

### Getting Your Freshdesk API Key

1. Log in to your Freshdesk account
2. Click on your profile icon (bottom left)
3. Go to **Security Settings**
4. Scroll down to **API Key** section
5. Copy your API key

### Setting Up Environment Variables

Replace the following values in your configuration:

- `FRESHDESK_API_KEY`: Your Freshdesk API key (obtained from the steps above)
- `FRESHDESK_DOMAIN`: Your Freshdesk domain (e.g., "yourcompany.freshdesk.com")

**Note**: The domain should be just the subdomain part without `https://` or `.freshdesk.com` appended.

## Usage

The server exposes various tools through the MCP protocol. Here are some key features:

### Filter Tickets

The `filter_tickets` tool allows you to filter tickets with advanced capabilities:

#### Filter by Assignee Name

```python
# Filter tickets assigned to a specific agent by name
await filter_tickets(assignee_name="John Doe")

# Or by email
await filter_tickets(assignee_name="john.doe@example.com")
```

#### Filter with Query Hash

You can use the native Freshdesk query_hash format for complex filtering:

```python
query_hash = [
    {
        "condition": "responder_id",
        "operator": "is_in",
        "type": "default",
        "value": [50000560730]
    },
    {
        "condition": "status",
        "operator": "is_in",
        "type": "default",
        "value": [2]  # Open status
    }
]
await filter_tickets(query_hash=query_hash)
```

#### Filter with Helper Parameters

The tool supports helper parameters that are automatically converted to query_hash:

```python
# Filter by status
await filter_tickets(status=2)

# Filter by priority
await filter_tickets(priority=3)

# Combine multiple filters
await filter_tickets(assignee_name="John Doe", status=2, priority=3)
```

#### Filter by Custom Fields

You can also filter by custom fields using the query_hash format:

```python
query_hash = [
    {
        "condition": "cf_request_for",  # Custom field
        "operator": "is_in",
        "type": "custom_field",
        "value": ["ITPM"]
    }
]
await filter_tickets(query_hash=query_hash)
```

### Get Unresolved Tickets Assigned to Me

The `get_unresolved_tickets_assigned_to_me` tool automatically retrieves all unresolved tickets assigned to the current authenticated user:

```python
# Get my unresolved tickets (no parameters needed)
result = await get_unresolved_tickets_assigned_to_me()
```

### Get Unresolved Tickets Assigned to Agent

The `get_unresolved_tickets_assigned_to_agent` tool retrieves unresolved tickets assigned to a specific agent:

```python
# Get unresolved tickets by agent name
result = await get_unresolved_tickets_assigned_to_agent(assignee_name="john.doe@example.com")

# Get unresolved tickets by agent ID
result = await get_unresolved_tickets_assigned_to_agent(assignee_id=50000560730)
```

### Get Unresolved Tickets by Squad

The `get_unresolved_tickets_by_squad` tool filters tickets for L2 Teams squad members using custom fields:

```python
# Get unresolved tickets for a squad member (L2 Teams is default)
result = await get_unresolved_tickets_by_squad(squad="Dracarys")

# Get open tickets for a squad
result = await get_unresolved_tickets_by_squad(
    squad="Dracarys",
    status="open"
)

# Get pending tickets
result = await get_unresolved_tickets_by_squad(
    squad="Dracarys",
    status="pending"
)
```

Parameters:
- `squad` (required): Squad member name (custom field)
- `status` (optional): Status to filter by (default: "unresolved")
  - Valid options: "unresolved", "open", "pending", "resolved", "awaiting_l2_response"

### Find Similar Tickets Using AI Copilot

The `find_similar_tickets_using_copilot` tool uses Freshdesk's AI Copilot to find similar tickets:

```python
# Find similar tickets using AI
result = await find_similar_tickets_using_copilot(ticket_id=12345)
```

This tool leverages Freshdesk's AI to analyze the ticket and find similar past tickets with intelligent insights.

### Search Tickets

The `search_tickets` tool performs general text-based searches for tickets:

```python
# Search by ticket ID
result = await search_tickets(ticket_id=12345)

# Search by query text
result = await search_tickets(query="login issue")
```

### Complete Filter Parameters

- `assignee_name`: Filter by assignee name or email (resolved to responder_id automatically)
- `status`: Filter by ticket status (integer)
- `priority`: Filter by ticket priority (integer)
- `query_hash`: Native Freshdesk filter format (array of condition objects)
- `page`: Page number (default: 1)
- `per_page`: Results per page (default: 100, max: 100)
- `order_by`: Field to sort by (default: "created_at")
- `order_type`: Sort direction - "asc" or "desc" (default: "desc")
- `exclude`: Fields to exclude from response (default: "custom_fields")
- `include`: Fields to include in response (default: "requester,stats,company,survey")

## API Reference

For the complete API reference, see the `server.py` file. Each function includes detailed docstrings.

## Testing

Run the test suite:

```bash
python tests/test-fd-mcp.py
```

## Troubleshooting

### MCP Server Not Connecting

If the MCP server is not connecting in Cursor or Claude Desktop:

1. **Verify Python is installed**: Run `python --version` in your terminal
2. **Verify package is installed**: Run `pip list | grep freshdesk-mcp-support`
3. **Check environment variables**: Ensure `FRESHDESK_API_KEY` and `FRESHDESK_DOMAIN` are correctly set
4. **Check logs**: Look for error messages in Cursor's MCP panel or Claude Desktop's console

### Authentication Errors

If you're getting authentication errors:

1. **Verify API key**: Make sure your API key is correct and hasn't expired
2. **Check domain**: Ensure the domain format is correct (just the subdomain, e.g., "yourcompany")
3. **Verify API access**: Log into Freshdesk and confirm API access is enabled for your account

### Module Not Found Errors

If you see "Module not found" errors:

1. **Reinstall the package**: `pip install --upgrade freshdesk-mcp-support`
2. **Check Python path**: Ensure the correct Python version is being used
3. **Use Option B**: Try the "Python directly" configuration instead of `uv`

### Platform-Specific Issues

**Mac:**
- Ensure you have the correct path: `~/Library/Application Support/Claude/`
- Check file permissions on the config file

**Windows:**
- Navigate to `%APPDATA%\Claude` using File Explorer
- Ensure the JSON file is valid (no extra commas, proper quotes)

**Linux:**
- Check file permissions: `chmod 600 ~/.config/Claude/claude_desktop_config.json`
- Verify Python is in your PATH: `which python`

## License

MIT

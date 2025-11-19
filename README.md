# freshdesk_mcp

A Model Context Protocol (MCP) server for interacting with the Freshdesk API.


## Available Tools

📥 **`my-unresolved-tickets`** – Instantly shows all unresolved tickets assigned to you (current user)

🧠 **`ticket-summary-insights`** – Generates a clean, detailed summary of ticket conversations – Provides key insights + suggested resolutions based on similar past tickets

🤖 **`find-similar-tickets-using-ai`** – Uses Freshdesk AI API to surface similar historical tickets – Offers in-depth recommended resolutions to speed up troubleshooting ⚡

## Coming Soon

The following tools will be available in the next version:

- **`add-ticket-reply`** - Add replies/first responses to tickets with customizable messages
- **`get-all-unresolved-tickets-in-a-squad`** - Get all unresolved tickets filtered by squad name with intelligent squad name validation

## Installation

### Get Your Freshdesk API Key
1. Log into Freshdesk → Profile → Security Settings → Copy API Key
2. Note your Freshdesk domain (e.g., `yourcompany.freshdesk.com`)

---

## Install in Cursor IDE

### Recommended: Using `uvx` (Auto-install)

1. **Install `uv`** (one-time setup):

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

2. **Configure Cursor IDE:**
   - Open Cursor IDE
   - Open Settings (⌘ + , on Mac, or Ctrl + , on Windows/Linux)
   - Search for "MCP Servers"
   - Add the following configuration:

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

3. **Restart Cursor IDE** and verify the MCP server is connected.

### Manual Installation (Not Recommended)

<details>
<summary>Click to expand manual installation options</summary>

**Option 1: Using Python directly**
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
*Requires: `pip install freshdesk-mcp-support` first*

**Option 2: Direct script execution**
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
*Requires: `pip install freshdesk-mcp-support` first*

</details>

---

## Install in Claude Desktop

### Recommended: Using `uvx` (Auto-install)

1. **Install `uv`** (one-time setup):

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

2. **Configure Claude Desktop:**

   **For Mac:**
   - Open Finder
   - Press `⌘ + Shift + G` and navigate to: `~/Library/Application Support/Claude/`
   - Open or create `claude_desktop_config.json`
   - Add the following configuration:

   **For Windows:**
   - Press `Win + R`
   - Type `%APPDATA%\Claude` and press Enter
   - Open or create `claude_desktop_config.json`
   - Add the following configuration:

   **For Linux:**
   - Navigate to `~/.config/Claude/`
   - Open or create `claude_desktop_config.json`
   - Add the following configuration:

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

3. **Restart Claude Desktop** and verify the MCP server is connected.

### Manual Installation (Not Recommended)

<details>
<summary>Click to expand manual installation options</summary>

**Option 1: Using Python directly**
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
*Requires: `pip install freshdesk-mcp-support` first*

**Option 2: Direct script execution**
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
*Requires: `pip install freshdesk-mcp-support` first*

</details>

---

## Local Development Installation

For development purposes:

```bash
pip install -e .
```

## Usage

The server exposes various tools through the MCP protocol. Here are the available tools:

### Get Ticket Summary with Insights

The `ticket-summary-insights` tool provides comprehensive ticket summaries including conversations, escalation indicators, action items, and similar tickets:

```python
# Get comprehensive summary for a ticket
result = await ticket_summary_insights(ticket_id=18963595)
```

**Features:**
- Ticket overview (ID, subject, status, priority, dates, tags)
- Full description
- Conversation summary and analysis
- Escalation indicators (keywords like "urgent", "critical", "blocked")
- Recent action items extracted from conversations
- Latest public conversations
- Similar tickets from AI Copilot (top 5, optimized for response size)
- Resolution recommendations

**Query examples:**
- "summary of ticket 12345"
- "ticket 12345 details"
- "what's the status of ticket 12345"
- "get ticket 12345 summary"
- "show me ticket 12345"
- "ticket 12345 information"
- "details for ticket 12345"
- "what is ticket 12345 about"
- "ticket 12345 overview"
- "tell me about ticket 12345"
- "ticket 12345 full details"
- "get details of ticket 12345"
- "ticket 12345 complete information"
- "ticket 12345 summary and conversations"

### Find Similar Tickets Using AI Copilot

The `find-similar-tickets-using-ai` tool uses Freshdesk's AI Copilot to find similar tickets:

```python
# Find similar tickets using AI
result = await find_similar_tickets_using_copilot(ticket_id=12345)
```

**Features:**
- AI-powered ticket similarity analysis
- Confidence scores for each similar ticket
- AI-generated summaries and resolutions
- Helps identify duplicate tickets and related issues

**Query examples:**
- "find similar tickets to 12345"
- "show me similar tickets for ticket 12345"
- "ticket 12345 similar issues"
- "find related tickets for 12345"
- "what tickets are similar to 12345"
- "ticket 12345 find duplicates"
- "search for similar tickets to 12345"
- "ticket 12345 related cases"
- "show similar tickets like 12345"
- "ticket 12345 find matches"
- "get similar tickets for ticket 12345"
- "ticket 12345 find comparable tickets"
- "ticket 12345 similar problems"
- "find tickets similar to ticket 12345"

### Get My Unresolved Tickets

The `my-unresolved-tickets` tool automatically retrieves all unresolved tickets assigned to the current authenticated user:

```python
# Get my unresolved tickets (no parameters needed)
result = await my_unresolved_tickets()
```

**Features:**
- Automatically detects current user from API
- Fetches Open (2), Pending (3), and status > 6 tickets
- Returns formatted table with ticket details
- Includes ticket URLs, status, priority, and due dates

**Query examples:**
- "my tickets"
- "my resolved tickets"
- "Get my tickets"
- "get all my tickets"
- "Get my unresolved tickets"
- "tickets assigned to me"


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

# freshdesk_mcp

A Model Context Protocol (MCP) server for interacting with the Freshdesk API.

## Features
- **Advanced ticket filtering with assignee name support** (NEW!)
- **Get unresolved tickets assigned to me** (NEW!)
- **Get current user's agent ID** (NEW!)
- **Get unresolved tickets by team** (NEW!)

## Installation

```bash
pip install -e .
```

## Configuration

Set the following environment variables:

- `FRESHDESK_API_KEY`: Your Freshdesk API key
- `FRESHDESK_DOMAIN`: Your Freshdesk domain (e.g., "yourcompany.freshdesk.com")

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

### Get Unresolved Tickets

The `get_unresolved_tickets` tool is a specialized function to get all unresolved tickets assigned to a specific agent:

```python
# Get my unresolved tickets by name
await get_unresolved_tickets(assignee_name="john.doe@example.com")

# Get unresolved tickets by ID
await get_unresolved_tickets(assignee_id=50000560730)

# Get unresolved tickets with specific status
await get_unresolved_tickets(assignee_id=50000560730, status=[2, 3])  # Open and Pending

# Get unresolved tickets for the current user
await get_unresolved_tickets
```

### Get Current Agent ID

The `get_current_agent_id` tool fetches the current authenticated user's agent information:

```python
# Get current agent information
result = await get_current_agent_id()
agent_id = result.get("agent", {}).get("id")
```

This is useful for automatically filtering tickets assigned to the current user without needing to know their ID upfront.

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

## License

MIT

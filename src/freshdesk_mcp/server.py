import httpx
from mcp.server.fastmcp import FastMCP
import logging
import os
import base64
from typing import Optional, Dict, Union, Any, List
from enum import IntEnum
import re

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize FastMCP server
mcp = FastMCP("freshdesk-mcp")

FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")
FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")

# Cache for authorization header to avoid recomputing base64 encoding
_auth_header = None


def _get_auth_headers() -> Dict[str, str]:
    """Get cached authentication headers."""
    global _auth_header
    if _auth_header is None:
        auth_string = f'{FRESHDESK_API_KEY}:X'
        encoded = base64.b64encode(auth_string.encode()).decode()
        _auth_header = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }
    return _auth_header.copy()


class TicketStatus(IntEnum):
    """Freshdesk ticket status values"""
    UNRESOLVED = 0
    OPEN = 2
    PENDING = 3
    RESOLVED = 4
    AWAITING_L2_RESPONSE = 10


class PaginationDefaults:
    """Default pagination values"""
    PAGE = 1
    PER_PAGE = 100
    MAX_PER_PAGE = 100
    MIN_PER_PAGE = 1


class TicketPriority(IntEnum):
    """Freshdesk ticket priority values"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


def parse_link_header(link_header: str) -> Dict[str, Optional[int]]:
    """Parse the Link header to extract pagination information.

    Args:
        link_header: The Link header string from the response

    Returns:
        Dictionary containing next and prev page numbers
    """
    pagination = {
        "next": None,
        "prev": None
    }

    if not link_header:
        return pagination

    # Split multiple links if present
    links = link_header.split(',')

    for link in links:
        # Extract URL and rel
        match = re.search(r'<(.+?)>;\s*rel="(.+?)"', link)
        if match:
            url, rel = match.groups()
            # Extract page number from URL
            page_match = re.search(r'page=(\d+)', url)
            if page_match:
                page_num = int(page_match.group(1))
                pagination[rel] = page_num

    return pagination


async def _resolve_agent_name_to_id(agent_name: str) -> Optional[int]:
    """Helper function to resolve agent name to agent ID."""
    if not agent_name:
        return None

    # First, try to check if it's already a numeric ID
    try:
        return int(agent_name)
    except ValueError:
        pass

    # Search for agents with the given name
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/agents"
    headers = _get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            # Search through agents
            page = PaginationDefaults.PAGE
            while page < PaginationDefaults.MAX_PER_PAGE:  # Prevent infinite loop
                params = {"page": page, "per_page": PaginationDefaults.PER_PAGE}
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                agents = response.json()

                if not agents:
                    break

                # Search for matching name or email
                for agent in agents:
                    if (agent.get("contact", {}).get("name") and
                        agent_name.lower() in agent["contact"]["name"].lower()):
                        return agent["id"]
                    if (agent.get("contact", {}).get("email") and
                        agent_name.lower() in agent["contact"]["email"].lower()):
                        return agent["id"]

                # Check for next page
                link_header = response.headers.get('Link', '')
                pagination_info = parse_link_header(link_header)
                if pagination_info.get("next"):
                    page = pagination_info.get("next")
                else:
                    break
        except Exception as e:
            logging.error(f"Error resolving agent name: {str(e)}")

    return None


async def _get_current_agent_id() -> Optional[int]:
    """Helper function to get the current logged-in agent's ID.

    Returns:
        Agent ID of the current user, or None if unable to fetch
    """
    url = f"https://{FRESHDESK_DOMAIN}/api/_/bootstrap/me"
    headers = _get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Extract agent ID from response
            agent = data.get("agent", {})
            if agent and "id" in agent:
                return agent["id"]
        except Exception as e:
            logging.error(f"Error fetching current agent ID: {str(e)}")

    return None


@mcp.tool()
async def get_tickets(page: Optional[int] = PaginationDefaults.PAGE, per_page: Optional[int] = 30) -> Dict[str, Any]:
    """Get tickets from Freshdesk with pagination support."""
    # Validate input parameters
    if page < PaginationDefaults.MIN_PER_PAGE:
        return {"error": f"Page number must be greater than or equal to {PaginationDefaults.MIN_PER_PAGE}"}

    if per_page < PaginationDefaults.MIN_PER_PAGE or per_page > PaginationDefaults.MAX_PER_PAGE:
        return {"error": f"Page size must be between {PaginationDefaults.MIN_PER_PAGE} and {PaginationDefaults.MAX_PER_PAGE}"}

    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets"

    params = {
        "page": page,
        "per_page": per_page
    }

    headers = _get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            # Parse pagination from Link header
            link_header = response.headers.get('Link', '')
            pagination_info = parse_link_header(link_header)

            tickets = response.json()

            return {
                "tickets": tickets,
                "pagination": {
                    "current_page": page,
                    "next_page": pagination_info.get("next"),
                    "prev_page": pagination_info.get("prev"),
                    "per_page": per_page
                }
            }

        except httpx.HTTPStatusError as e:
            return {"error": f"Failed to fetch tickets: {str(e)}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


async def filter_tickets(
    query_hash: Optional[List[Dict[str, Any]]] = None,
    assignee_name: Optional[str] = None,
    status: Optional[Union[int, str]] = None,
    priority: Optional[Union[int, str]] = None,
    page: Optional[int] = PaginationDefaults.PAGE,
    per_page: Optional[int] = PaginationDefaults.PER_PAGE,
    order_by: Optional[str] = "created_at",
    order_type: Optional[str] = "desc",
    exclude: Optional[str] = "custom_fields",
    include: Optional[str] = "requester,stats,company,survey"
) -> Dict[str, Any]:
    """Filter tickets in Freshdesk using query_hash format or helper parameters.

    This tool supports advanced filtering using either:
    1. Native query_hash format (array of condition objects)
    2. Helper parameters like assignee_name, status, priority (automatically converted to query_hash)

    Args:
        query_hash: List of filter conditions in native Freshdesk format. Each condition has:
            - condition: Field name (e.g., "responder_id", "status", "cf_custom_field_name", "freshservice_teams")
            - operator: Comparison operator (e.g., "is_in", "is", "greater_than")
            - type: "default" or "custom_field"
            - value: Value(s) to match (can be array for "is_in")
        assignee_name: Filter by assignee name or email (will be resolved to responder_id)
        status: Filter by status (will be added to query_hash)
        priority: Filter by priority (will be added to query_hash)
        page: Page number (default: 1)
        per_page: Results per page (default: 100)
        order_by: Field to sort by (default: "created_at")
        order_type: Sort direction - "asc" or "desc" (default: "desc")
        exclude: Fields to exclude from response (default: "custom_fields")
        include: Fields to include in response (default: "requester,stats,company,survey")

    Returns:
        Dictionary with tickets and pagination information

    Examples:
        # Filter with default fields
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
                "value": [0]  # 0=New, 2=Open, 3=Pending, 4=Resolved, 5=Closed
            }
        ]

        # Filter with custom fields
        query_hash = [
            {
                "condition": "freshservice_teams",
                "operator": "is_in",
                "type": "custom_field",
                "value": ["L2 Teams"]
            },
            {
                "condition": "team_member",
                "operator": "is_in",
                "type": "custom_field",
                "value": ["Dracarys"]
            },
            {
                "condition": "cf_request_for",
                "operator": "is_in",
                "type": "custom_field",
                "value": ["ITPM"]
            }
        ]
    """
    # Validate input parameters
    if page < PaginationDefaults.MIN_PER_PAGE:
        return {"error": f"Page number must be greater than or equal to {PaginationDefaults.MIN_PER_PAGE}"}

    if per_page < PaginationDefaults.MIN_PER_PAGE or per_page > PaginationDefaults.MAX_PER_PAGE:
        return {"error": f"Page size must be between {PaginationDefaults.MIN_PER_PAGE} and {PaginationDefaults.MAX_PER_PAGE}"}

    # Build query_hash if using helper parameters
    filters = []

    # Resolve assignee name to ID if provided
    if assignee_name:
        assignee_id = await _resolve_agent_name_to_id(assignee_name)
        if assignee_id:
            filters.append({
                "condition": "responder_id",
                "operator": "is_in",
                "type": "default",
                "value": [assignee_id]
            })
        else:
            return {"error": f"Could not resolve assignee name: {assignee_name}"}

    # Add status filter if provided
    if status is not None:
        filters.append({
            "condition": "status",
            "operator": "is_in",
            "type": "default",
            "value": [int(status)]
        })

    # Add priority filter if provided
    if priority is not None:
        filters.append({
            "condition": "priority",
            "operator": "is_in",
            "type": "default",
            "value": [int(priority)]
        })

    # Merge with provided query_hash
    if query_hash:
        filters.extend(query_hash)

    if not filters:
        return {"error": "At least one filter condition is required"}

    # Use the filtered tickets API endpoint
    url = f"https://{FRESHDESK_DOMAIN}/api/_/tickets"

    # Build query parameters
    params = {
        "page": page,
        "per_page": per_page,
        "order_by": order_by,
        "order_type": order_type,
        "exclude": exclude,
        "include": include
    }

    # Add query_hash parameters
    for idx, filter_condition in enumerate(filters):
        params[f"query_hash[{idx}][condition]"] = filter_condition.get("condition")
        params[f"query_hash[{idx}][operator]"] = filter_condition.get("operator")
        params[f"query_hash[{idx}][type]"] = filter_condition.get("type", "default")

        # Handle value - could be single value or array
        value = filter_condition.get("value")
        if isinstance(value, list):
            for val_idx, val in enumerate(value):
                params[f"query_hash[{idx}][value][{val_idx}]"] = val
        else:
            params[f"query_hash[{idx}][value]"] = value

    headers = _get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            # Parse pagination from Link header
            link_header = response.headers.get('Link', '')
            pagination_info = parse_link_header(link_header)

            tickets = response.json()

            return {
                "tickets": tickets,
                "pagination": {
                    "current_page": page,
                    "next_page": pagination_info.get("next"),
                    "prev_page": pagination_info.get("prev"),
                    "per_page": per_page
                },
                "filters_applied": filters
            }

        except httpx.HTTPStatusError as e:
            error_details = f"Failed to filter tickets: {str(e)}"
            try:
                if e.response:
                    error_details += f" - {e.response.json()}"
            except:
                pass
            return {"error": error_details}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


@mcp.tool()
async def get_ticket(ticket_id: int):
    """Get a ticket in Freshdesk."""
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}"
    headers = _get_auth_headers()

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()


@mcp.tool()
async def find_similar_tickets_using_copilot(ticket_id: int) -> Dict[str, Any]:
    """Find similar tickets using Freshdesk Copilot AI.

    This tool uses the Copilot API to find tickets similar to the given ticket ID.
    It returns tickets with AI-generated summaries, resolution details, and confidence scores.

    Args:
        ticket_id: The ID of the ticket to find similar tickets for

    Returns:
        Dictionary with similar_tickets array containing:

    Example:
        # Find similar tickets for ticket 12345
        result = await find_similar_tickets(ticket_id=12345)
    """
    if not ticket_id or ticket_id < 1:
        return {"error": "Invalid ticket_id. Must be a positive integer."}

    url = f"https://{FRESHDESK_DOMAIN}/api/_/copilot/tickets/{ticket_id}/similar_tickets"
    headers = _get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"Failed to find similar tickets: {str(e)}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


@mcp.tool()
async def search_tickets(ticket_id: Optional[int] = None, query: Optional[str] = None):
    """Search for tickets in Freshdesk using text search."""
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/search/tickets"
    headers = {
        "Authorization": f"Basic {base64.b64encode(f'{FRESHDESK_API_KEY}:X'.encode()).decode()}"
    }
    if ticket_id is not None:
        ticket = await get_ticket(ticket_id)
        query = ticket["subject"]
    else:
        query = query
    params = {"query": query}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        return response.json()

async def search_agents(query: str) -> list[Dict[str, Any]]:
    """Search for agents in Freshdesk."""
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/agents/autocomplete?term={query}"
    headers = {
        "Authorization": f"Basic {base64.b64encode(f'{FRESHDESK_API_KEY}:X'.encode()).decode()}"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return response.json()

@mcp.tool()
async def get_unresolved_tickets_assigned_to_me() -> Dict[str, Any]:
    """Get all unresolved tickets assigned to me.

    This tool automatically fetches the current user's agent ID and filters
    for unresolved tickets (status 0) assigned to them.

    Returns:
        Dictionary with tickets and pagination information

    Example:
        # Get my unresolved tickets
        result = await get_unresolved_tickets_assigned_to_me()
    """
    # Get current user's agent ID
    assignee_id = await _get_current_agent_id()
    if not assignee_id:
        return {"error": "Could not fetch current agent ID"}

    # Build query_hash for unresolved status
    query_hash = [
        {
            "condition": "status",
            "operator": "is_in",
            "type": "default",
            "value": [TicketStatus.UNRESOLVED.value]
        },
        {
            "condition": "responder_id",
            "operator": "is_in",
            "type": "default",
            "value": [assignee_id]
        }
    ]

    # Call filter_tickets with the query_hash
    return await filter_tickets(
        query_hash=query_hash,
        page=PaginationDefaults.PAGE,
        per_page=PaginationDefaults.PER_PAGE
    )


@mcp.tool()
async def get_unresolved_tickets_assigned_to_agent(
    assignee_name: Optional[str] = None,
    assignee_id: Optional[int] = None
) -> Dict[str, Any]:
    """Get all unresolved tickets assigned to a specific agent.

    This tool filters tickets by status (unresolved) and assignee.
    Either assignee_name or assignee_id must be provided.

    Args:
        assignee_name: Agent name or email (will be resolved to responder_id).
        assignee_id: Direct agent ID (responder_id) to filter by

    Returns:
        Dictionary with tickets and pagination information

    Example:
        # Get unresolved tickets by name
        result = await get_unresolved_tickets_assigned_to_agent(assignee_name="John Doe")

        # Get unresolved tickets by ID
        result = await get_unresolved_tickets_assigned_to_agent(assignee_id=50000560730)
    """
    # Validate that we have an assignee identifier
    if not assignee_name and not assignee_id:
        return {"error": "Either assignee_name or assignee_id must be provided"}

    # Resolve assignee name to ID if needed
    if assignee_name:
        resolved_id = await _resolve_agent_name_to_id(assignee_name)
        if not resolved_id:
            return {"error": f"Could not resolve assignee name: {assignee_name}"}
        assignee_id = resolved_id

    # Build query_hash for unresolved status
    query_hash = [
        {
            "condition": "status",
            "operator": "is_in",
            "type": "default",
            "value": [TicketStatus.UNRESOLVED.value]
        },
        {
            "condition": "responder_id",
            "operator": "is_in",
            "type": "default",
            "value": [assignee_id]
        }
    ]

    # Call filter_tickets with the query_hash
    return await filter_tickets(
        query_hash=query_hash,
        page=PaginationDefaults.PAGE,
        per_page=PaginationDefaults.PER_PAGE
    )


@mcp.tool()
async def get_unresolved_tickets_by_squad(
    squad: Optional[str] = None,
    page: Optional[int] = PaginationDefaults.PAGE,
    per_page: Optional[int] = PaginationDefaults.PER_PAGE,
) -> Dict[str, Any]:
    """Get all unresolved tickets assigned to a squad in L2 Teams.

    This tool filters tickets by status for L2 Teams squad members.
    By default, it filters for unresolved (0).

    Args:
        squad: Squad member name (required). This is a custom field filter.
        page: Page number (default: 1)
        per_page: Results per page (default: 100, max: 100)

    Note: Always filters for unresolved status (0).

    Returns:
        Dictionary with tickets and pagination information

    Example:
        # Get unresolved tickets for a squad member
        result = await get_unresolved_tickets_by_squad(squad="Dracarys")
    """
    # Build query_hash with team filters
    # Always filter by L2 Teams and unresolved status
    query_hash = [
        {
            "condition": "status",
            "operator": "is_in",
            "type": "default",
            "value": [TicketStatus.UNRESOLVED.value]
        },
        {
            "condition": "freshservice_teams",
            "operator": "is_in",
            "type": "custom_field",
            "value": ["L2 Teams"]
        },
        {
            "condition": "team_member",
            "operator": "is_in",
            "type": "custom_field",
            "value": [squad]
        }
    ]

    # Call filter_tickets with the query_hash
    return await filter_tickets(
        query_hash=query_hash,
        page=page,
        per_page=per_page
    )


def main():
    logging.info("Starting Freshdesk MCP server")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()

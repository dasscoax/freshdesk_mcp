import httpx
from mcp.server.fastmcp import FastMCP
import logging
import os
from typing import Optional, Dict, Union, Any, List
from enum import IntEnum
import re

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize FastMCP server
mcp = FastMCP("freshdesk-mcp")

FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")
FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")

def _get_auth_headers() -> Dict[str, str]:
    """Get authentication headers."""
    return {
        "Content-Type": "application/json"
    }


def _get_auth() -> tuple:
    """Get basic auth credentials for httpx.
    
    Equivalent to Ruby's:
    - authenticate_using_basic = true
    - set_basic_auth('FRESHDESK_API_KEY', 'X')
    """
    return (FRESHDESK_API_KEY, 'X')


class TicketStatus(IntEnum):
    """Freshdesk ticket status values"""
    UNRESOLVED = 0
    OPEN = 2
    PENDING = 3
    RESOLVED = 4


class TicketPriority(IntEnum):
    """Freshdesk ticket priority values"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


def _get_status_name(status_id: Optional[int]) -> str:
    """Convert status ID to readable name."""
    if status_id is None:
        return "Unknown"
    # Status IDs 6-39 are "In Progress"
    if 6 <= status_id <= 39:
        return "Custom Status"
    status_map = {
        0: "Unresolved",
        2: "Open",
        3: "Pending",
        4: "Resolved",
        5: "Closed"
    }
    return status_map.get(status_id, f"Unknown ({status_id})")


def _get_priority_name(priority_id: Optional[int]) -> str:
    """Convert priority ID to readable name."""
    if priority_id is None:
        return "Unknown"
    priority_map = {
        1: "Low",
        2: "Medium",
        3: "High",
        4: "Urgent"
    }
    return priority_map.get(priority_id, f"Unknown ({priority_id})")


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

async def _get_current_agent_id() -> Optional[int]:
    """Helper function to get the current user's agent ID from /api/v2/agents/me.
    
    Returns:
        Agent ID (int) if found, None otherwise
    """
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/agents/me"
    headers = _get_auth_headers()
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, auth=_get_auth())
            response.raise_for_status()
            data = response.json()
            
            # Extract agent ID from response
            agent_id = data.get("id")
            
            if agent_id:
                return int(agent_id)
            return None
        except httpx.HTTPStatusError as e:
            logging.error(f"Error getting current agent ID: {str(e)}")
        except Exception as e:
            logging.error(f"Error getting current agent ID: {str(e)}")
    
    return None


async def _resolve_agent_id_to_name(responder_id: int) -> Optional[str]:
    """Helper function to resolve responder ID to agent name.
    
    Args:
        responder_id: The agent/responder ID to resolve
        
    Returns:
        Agent name if found, None otherwise
    """
    if not responder_id:
        return None
    
    url = f"https://{FRESHDESK_DOMAIN}/api/agents/{responder_id}"
    headers = _get_auth_headers()
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, auth=_get_auth())
            response.raise_for_status()
            data = response.json()
            
            # Extract name from agent.user.name
            agent = data.get("agent", {})
            user = agent.get("user", {})
            name = user.get("name")
            
            return name if name else None
        except httpx.HTTPStatusError as e:
            logging.error(f"Error resolving agent ID {responder_id}: {str(e)}")
        except Exception as e:
            logging.error(f"Error resolving agent ID {responder_id}: {str(e)}")
    
    return None


@mcp.tool()
async def get_tickets() -> Dict[str, Any]:
    """Get all tickets in freshdesk"""

    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets"

    params = {
        "page": 1,
        "per_page": 30
    }

    headers = _get_auth_headers()

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, params=params, auth=_get_auth())
            response.raise_for_status()

            # Parse pagination from Link header
            link_header = response.headers.get('Link', '')
            pagination_info = parse_link_header(link_header)

            tickets = response.json()

            return {
                "tickets": tickets,
                "pagination": {
                    "current_page": 1,
                    "next_page": pagination_info.get("next"),
                    "prev_page": pagination_info.get("prev"),
                    "per_page": 30
                }
            }

        except httpx.HTTPStatusError as e:
            return {"error": f"Failed to fetch tickets: {str(e)}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


async def filter_tickets(
    query_hash: Optional[List[Dict[str, Any]]] = None,
    responder_id: Optional[str] = None,
    status: Optional[Union[int, str]] = None,
    priority: Optional[Union[int, str]] = None,
    page: Optional[int] = 1,
    per_page: Optional[int] = 30,
    order_by: Optional[str] = "created_at",
    order_type: Optional[str] = "desc",
    exclude: Optional[str] = "custom_fields",
    include: Optional[str] = "requester,stats,company,survey"
) -> Dict[str, Any]:
    """Filter tickets in Freshdesk using query_hash format or helper parameters.

    This tool supports advanced filtering using either:
    1. Native query_hash format (array of condition objects)
    2. Helper parameters like responder_id, status, priority (automatically converted to query_hash)

    Args:
        query_hash: List of filter conditions in native Freshdesk format. Each condition has:
            - condition: Field name (e.g., "responder_id", "status", "cf_custom_field_name", "freshservice_teams")
            - operator: Comparison operator (e.g., "is_in", "is", "greater_than")
            - type: "default" or "custom_field"
            - value: Value(s) to match (can be array for "is_in")
        responder_id: Filter by assignee ID (will be added to query_hash)
        status: Filter by status (will be added to query_hash)
        priority: Filter by priority (will be added to query_hash)
        page: Page number (default: 1)
        per_page: Results per page (default: 30)
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
    if page < 1:
        return {"error": f"Page number must be greater than or equal to 1"}

    if per_page < 1 or per_page > 100:
        return {"error": f"Page size must be between 1 and 100"}

    # Build query_hash if using helper parameters
    filters = []

    # Resolve responder_id (only if query_hash is not provided)
    if responder_id:
        filters.append({
            "condition": "responder_id",
            "operator": "is_in",
            "type": "default",
            "value": [responder_id]
        })
    # Only require responder_id if query_hash is not provided
    elif not query_hash:
        return {"error": f"Could not resolve responder details"}

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
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/search/tickets"

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

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, params=params, auth=_get_auth())
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
    """Get a ticket details by ticket ID"""
    url = f"https://{FRESHDESK_DOMAIN}/api/tickets/{ticket_id}"
    headers = _get_auth_headers()

    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url, headers=headers, auth=_get_auth())
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

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, auth=_get_auth())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"Failed to find similar tickets: {str(e)}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


@mcp.tool()
async def search_tickets(
    ticket_id: Optional[int] = None,
    search_value: Optional[str] = None
) -> Dict[str, Any]:
    """Search for tickets using text search by ticket ID or query text.
    
    Uses POST request with JSON body format with default values:
    - context: "spotlight" (default)
    - search_sort: "relevance" (default)
    - filter_params: {} (default)
    
    Args:
        ticket_id: Optional ticket ID to search by (will use ticket subject as term)
        search_value: Search value
    
    Returns:
        Dictionary with search results
    """
    url = f"https://{FRESHDESK_DOMAIN}/api/_/search/tickets"
    headers = _get_auth_headers()
    
    # Determine search term
    search_term = None
    if ticket_id is not None:
        ticket = await get_ticket(ticket_id)
        search_term = ticket.get("subject", "")
    elif search_value:
        search_term = search_value
    
    if not search_term:
        return {"error": "Either ticket_id, search_value must be provided"}
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            # Always use POST with JSON body format with default values
            payload = {
                "context": "spotlight",
                "term": search_term,
                "search_sort": "relevance",
                "filter_params": {}
            }
            response = await client.post(url, headers=headers, json=payload, auth=_get_auth())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_details = f"Failed to search tickets: {str(e)}"
            try:
                if e.response:
                    error_details += f" - {e.response.json()}"
            except:
                pass
            return {"error": error_details}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}

async def my_unresolved_tickets() -> Dict[str, Any]:
    """My unresolved tickets

    This tool automatically fetches the current user's agent ID and filters
    for unresolved tickets (status 0) assigned to them.
    
    Use this when you need to see tickets assigned to the current authenticated user.
    This is the best tool for queries like:
    - "my tickets"
    - "my resolved tickets" 
    - "Get my tickets"
    - "get all my tickets"
    - "Get my unresolved tickets"
    - "tickets assigned to me"
    - Any query asking about the current user's tickets

    Returns:
        Dictionary with tickets and pagination information

    Example:
        # Get my unresolved tickets
        result = await my_unresolved_tickets()
    """
    # Get current user's agent ID from API
    assignee_id = await _get_current_agent_id()
    
    if assignee_id is None:
        return {"error": "Could not get agent ID from API. Please check your authentication."}

    # Build query_hash for unresolved status
    query_hash = [
        {
            "condition": "status",
            "operator": "is_in",
            "type": "default",
            "value": [0]
        },
        {
            "condition": "responder_id",
            "operator": "is_in",
            "type": "default",
            "value": [assignee_id]
        }
    ]

    # Call filter_tickets with the query_hash
    result = await filter_tickets(
        query_hash=query_hash,
        page=1,
        per_page=30
    )
    
    # Check if there was an error
    if "error" in result:
        return result
    
    # Format tickets with URLs and readable structure
    formatted_tickets = []
    tickets = result.get("tickets", [])
    
    for ticket in tickets:
        ticket_id = ticket.get("id")
        ticket_url = f"https://{FRESHDESK_DOMAIN}/a/tickets/{ticket_id}"
        
        status_id = ticket.get("status")
        priority_id = ticket.get("priority")
        
        formatted_ticket = {
            "url": ticket_url,
            "subject": ticket.get("subject", "No subject"),
            "status": _get_status_name(status_id),
            "priority": _get_priority_name(priority_id),
            "resolution_due_by": ticket.get("due_by", "") 
        }
        
        # Only include fr_due_by if it exists
        if ticket.get("fr_due_by"):
            formatted_ticket["first_response_due_by"] = ticket.get("fr_due_by")
            
        formatted_tickets.append(formatted_ticket)
    
    # Build readable summary
    readable_summary = f"Found {len(formatted_tickets)} unresolved ticket(s) assigned to you:"
    
    # Create formatted response
    return {
        "summary": readable_summary,
        "ticket_count": len(formatted_tickets),
        "tickets": formatted_tickets,
        "pagination": result.get("pagination", {}),
        "raw_tickets": tickets  # Include raw data for detailed access if needed
    }

@mcp.tool()
async def my_unresolved_tickets_v2(
    page: Optional[int] = 1
) -> Dict[str, Any]:
    """Get my unresolved tickets using v2 query API.

    This tool uses the v2 search API with query parameter format to fetch
    unresolved tickets assigned to the current user.

    This is the best tool for queries like:
    - "my tickets"
    - "my resolved tickets" 
    - "Get my tickets"
    - "get all my tickets"
    - "Get my unresolved tickets"
    - "tickets assigned to me"
    - Any query asking about the current user's tickets
    
    Query format: agent_id:{agent_id} AND (status:2 OR status:3 OR status:>6)
    This includes Open (2), Pending (3), and any status greater than 6.
    
    The agent ID is automatically fetched from /api/v2/agents/me endpoint.

    Args:
        page: Page number (default: 1)

    Returns:
        Dictionary with tickets and pagination information

    Example:
        # Get my unresolved tickets using v2 API
        result = await my_unresolved_tickets_v2()
    """
    # Get current user's agent ID from API
    agent_id = await _get_current_agent_id()
    
    if agent_id is None:
        return {"error": "Could not get agent ID from API. Please check your authentication."}

    # Validate pagination parameters
    if page < 1:
        return {"error": "Page number must be greater than or equal to 1"}

    # Build query string: agent_id:{agent_id} AND (status:2 OR status:3 OR status:>6)
    query = f"agent_id:{agent_id} AND (status:2 OR status:3 OR status:>6)"

    # Use the v2 search API with query parameter
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/search/tickets"

    # Build query parameters
    params = {
        "query": query,
        "page": page
    }

    headers = _get_auth_headers()

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, params=params, auth=_get_auth())
            response.raise_for_status()

            # Parse pagination from Link header
            link_header = response.headers.get('Link', '')

            tickets = response.json()

            # Format tickets with URLs and readable structure
            formatted_tickets = []
            for ticket in tickets:
                ticket_id = ticket.get("id")
                ticket_url = f"https://{FRESHDESK_DOMAIN}/a/tickets/{ticket_id}"
                
                status_id = ticket.get("status")
                priority_id = ticket.get("priority")
                
                formatted_ticket = {
                    "ticket id": ticket_id,
                    "url": ticket_url,
                    "subject": ticket.get("subject", "No subject"),
                    "status": _get_status_name(status_id),
                    "priority": _get_priority_name(priority_id),
                    "resolution_due_by": ticket.get("due_by", "") 
                }
                
                # Only include fr_due_by if it exists
                if ticket.get("fr_due_by"):
                    formatted_ticket["first_response_due_by"] = ticket.get("fr_due_by")
                    
                formatted_tickets.append(formatted_ticket)

            # Build readable summary
            readable_summary = f"Found {len(formatted_tickets)} unresolved ticket(s) assigned to you:"

            return {
                "summary": readable_summary,
                "ticket_count": len(formatted_tickets),
                "tickets": formatted_tickets,
                "pagination": {
                    "current_page": page
                },
                "raw_tickets": tickets
            }

        except httpx.HTTPStatusError as e:
            error_details = f"Failed to fetch unresolved tickets: {str(e)}"
            try:
                if e.response:
                    error_details += f" - {e.response.json()}"
            except:
                pass
            return {"error": error_details}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


@mcp.tool()
async def get_all_unresolved_tickets_in_a_squad(
    squad: Optional[str] = None
) -> Dict[str, Any]:
    """Get all unresolved tickets in a squad

    By default, it filters for unresolved (0).

    Use this tool for queries like:
    - "all unresolved tickets in my squad"
    - "my team"
    - "team"
    - "open tickets in team"
    - "open tickets in squad"
    - "squad"
    - Any query asking about tickets in a squad or team

    Args:
        squad: Squad member name (required). This is a custom field filter.
        page: Page number (default: 1)
        per_page: Results per page (default: 30, max: 30)

    Note: Always filters for unresolved status (0).

    Returns:
        Dictionary with tickets and pagination information

    Example:
        # Get unresolved tickets for a squad member
        result = await get_all_unresolved_tickets_in_a_squad(squad="Dracarys")
    """
    # Build query_hash with team filters
    # Always filter by L2 Teams and unresolved status
    query_hash = [
        {
            "condition": "status",
            "operator": "is_in",
            "type": "default",
            "value": [0]
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
    result = await filter_tickets(
        query_hash=query_hash,
        page=1,
        per_page=30
    )
    
    # Check if there was an error
    if "error" in result:
        return result
    
    # Format tickets with URLs and readable structure
    formatted_tickets = []
    tickets = result.get("tickets", [])
    
    for ticket in tickets:
        ticket_id = ticket.get("id")
        ticket_url = f"https://{FRESHDESK_DOMAIN}/a/tickets/{ticket_id}"
        
        status_id = ticket.get("status")
        priority_id = ticket.get("priority")
        
        # Resolve responder ID to name
        responder_id = ticket.get("responder_id")
        responder_name = "Unassigned"
        if responder_id:
            resolved_name = await _resolve_agent_id_to_name(responder_id)
            responder_name = resolved_name if resolved_name else f"Agent ID: {responder_id}"

        formatted_ticket = {
            "subject": ticket.get("subject", "No subject"),
            "status": _get_status_name(status_id),
            "priority": _get_priority_name(priority_id),
            "responder": responder_name,
            "resolution_due_by": ticket.get("due_by", ""),
            "url": ticket_url,
        }
        
        # Only include fr_due_by if it exists
        if ticket.get("fr_due_by"):
            formatted_ticket["first_response_due_by"] = ticket.get("fr_due_by")
        
        formatted_tickets.append(formatted_ticket)
    
    # Build readable summary
    readable_summary = f"Found {len(formatted_tickets)} unresolved ticket(s) in squad"
    if squad:
        readable_summary += f" '{squad}'"
    readable_summary += ":"
    
    # Create formatted response
    return {
        "summary": readable_summary,
        "ticket_count": len(formatted_tickets),
        "tickets": formatted_tickets,
        "pagination": result.get("pagination", {}),
        "raw_tickets": tickets  # Include raw data for detailed access if needed
    }


def main():
    logging.info("Starting Freshdesk MCP support server")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()

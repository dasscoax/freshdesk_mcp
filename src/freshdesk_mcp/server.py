import httpx
from mcp.server.fastmcp import FastMCP
import logging
import os
from typing import Optional, Dict, Union, Any, List
from enum import IntEnum
import re
from datetime import datetime

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


@mcp.tool(name="ticket-summary-insights")
async def ticket_summary_insights(ticket_id: int) -> Dict[str, Any]:
    """Get comprehensive ticket summary with description and conversation insights.
    
    This tool fetches ticket details, all conversations, and similar tickets using Copilot AI,
    then provides a summary with important information to help resolve the ticket.
    
    Use this tool for queries like:
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
    
    Args:
        ticket_id: The ticket ID to get summary for (required)
    
    Returns:
        Dictionary with ticket summary, description, conversation insights, and similar tickets data
    
    Example:
        # Get summary for ticket 18963595
        result = await ticket_summary_insights(ticket_id=18963595)
    """
    # Get ticket details
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}"
    headers = _get_auth_headers()
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            # Fetch ticket details
            response = await client.get(url, headers=headers, auth=_get_auth())
            response.raise_for_status()
            ticket = response.json()
            
            if not isinstance(ticket, dict):
                return {"error": f"Unexpected ticket response format. Expected dict, got {type(ticket).__name__}"}
            
            # Get conversations
            conversations_result = await get_ticket_conversations(ticket_id)
            if "error" in conversations_result:
                conversations_summary = "Unable to fetch conversations"
                conversations = []
            else:
                conversations_summary = conversations_result.get("summary", "")
                conversations = conversations_result.get("conversations", [])
            
            # Get similar tickets using Copilot (limit to top 5 to avoid chat length issues)
            similar_tickets_result = await find_similar_tickets_using_ai(ticket_id)
            similar_tickets_data = None
            if "error" not in similar_tickets_result:
                # Extract and limit similar tickets to prevent chat length issues
                similar_tickets_list = similar_tickets_result.get("similar_tickets", [])
                if similar_tickets_list:
                    # Limit to top 5 similar tickets and extract only essential fields
                    limited_similar_tickets = []
                    for similar_ticket in similar_tickets_list[:5]:
                        limited_ticket = {
                            "ticket_id": similar_ticket.get("ticket_id"),
                            "confidence_score": similar_ticket.get("confidence_score"),
                            "summary": similar_ticket.get("summary", "")[:200] if similar_ticket.get("summary") else "",  # Truncate to 200 chars
                            "resolution": similar_ticket.get("resolution", "")[:200] if similar_ticket.get("resolution") else ""  # Truncate to 200 chars
                        }
                        limited_similar_tickets.append(limited_ticket)
                    
                    similar_tickets_data = {
                        "similar_tickets": limited_similar_tickets,
                        "total_found": len(similar_tickets_list),
                        "showing": len(limited_similar_tickets)
                    }
                else:
                    similar_tickets_data = similar_tickets_result
            
            # Extract key ticket information
            ticket_subject = ticket.get("subject", "No subject")
            ticket_status = _get_status_name(ticket.get("status"))
            ticket_priority = _get_priority_name(ticket.get("priority"))
            ticket_description = ticket.get("description_text", ticket.get("description", ""))
            ticket_created = _format_date(ticket.get("created_at", ""))
            ticket_updated = _format_date(ticket.get("updated_at", ""))
            ticket_due_by = _format_date(ticket.get("due_by", "")) if ticket.get("due_by") else None
            ticket_fr_due_by = _format_date(ticket.get("fr_due_by", "")) if ticket.get("fr_due_by") else None
            requester_id = ticket.get("requester_id")
            responder_id = ticket.get("responder_id")
            group_id = ticket.get("group_id")
            ticket_type = ticket.get("type", "")
            tags = ticket.get("tags", [])
            
            # Extract key conversation insights
            key_insights = []
            latest_public_conversations = []
            escalation_indicators = []
            action_items = []
            
            # Analyze conversations for important information
            for conv in conversations:
                body_text = conv.get("body_text", "").lower()
                is_private = conv.get("private", True)
                is_incoming = conv.get("incoming", False)
                
                # Check for escalation keywords
                if any(keyword in body_text for keyword in ["escalat", "urgent", "critical", "blocked", "stuck"]):
                    escalation_indicators.append(conv.get("created_at", ""))
                
                # Extract action items or requests
                if any(keyword in body_text for keyword in ["please", "need", "required", "can you", "update", "check"]):
                    if not is_private:
                        action_items.append(conv.get("body_text", "")[:150])
                
                # Collect public conversations (will take last 5 later)
                if not is_private:
                    latest_public_conversations.append({
                        "date": conv.get("created_at", ""),
                        "text": conv.get("body_text", "")[:200]
                    })
            
            # Build comprehensive summary
            summary_parts = []
            
            # Ticket Overview
            summary_parts.append(f"TICKET OVERVIEW:")
            summary_parts.append(f"  • ID: #{ticket_id}")
            summary_parts.append(f"  • Subject: {ticket_subject}")
            summary_parts.append(f"  • Status: {ticket_status}")
            summary_parts.append(f"  • Priority: {ticket_priority}")
            if ticket_type:
                summary_parts.append(f"  • Type: {ticket_type}")
            summary_parts.append(f"  • Created: {ticket_created}")
            summary_parts.append(f"  • Last Updated: {ticket_updated}")
            if ticket_due_by:
                summary_parts.append(f"  • Resolution Due: {ticket_due_by}")
            if ticket_fr_due_by:
                summary_parts.append(f"  • First Response Due: {ticket_fr_due_by}")
            if tags:
                summary_parts.append(f"  • Tags: {', '.join(tags[:5])}")
            
            # Description
            summary_parts.append(f"\nDESCRIPTION:")
            if ticket_description:
                # Truncate long descriptions
                desc_preview = ticket_description[:500] + "..." if len(ticket_description) > 500 else ticket_description
                summary_parts.append(f"  {desc_preview}")
            else:
                summary_parts.append("  No description available")
            
            # Conversation Summary
            summary_parts.append(f"\nCONVERSATION SUMMARY:")
            summary_parts.append(f"  {conversations_summary}")
            
            # Key Insights
            if escalation_indicators:
                summary_parts.append(f"\n⚠️  ESCALATION INDICATORS:")
                summary_parts.append(f"  Found {len(escalation_indicators)} conversation(s) with escalation keywords")
                summary_parts.append(f"  Latest: {escalation_indicators[-1] if escalation_indicators else 'N/A'}")
            
            if action_items:
                summary_parts.append(f"\n📋 RECENT ACTION ITEMS:")
                # Get the most recent 3 action items (last 3 in the list)
                recent_actions = action_items[-3:] if len(action_items) > 3 else action_items
                for i, item in enumerate(recent_actions, 1):
                    summary_parts.append(f"  {i}. {item}")
            
            if latest_public_conversations:
                summary_parts.append(f"\n💬 LATEST PUBLIC CONVERSATIONS:")
                # Get the most recent 3 conversations (last 3 in the list)
                recent_convs = latest_public_conversations[-3:] if len(latest_public_conversations) > 3 else latest_public_conversations
                for conv in recent_convs:
                    summary_parts.append(f"  [{conv['date']}] {conv['text']}")
            
            # Resolution Recommendations
            summary_parts.append(f"\n💡 RESOLUTION RECOMMENDATIONS:")
            if ticket_status in ["Open", "Pending"]:
                if conversations:
                    summary_parts.append(f"  • Review {len(conversations)} conversation(s) for context")
                    if escalation_indicators:
                        summary_parts.append(f"  • Address escalation concerns immediately")
                    if ticket_due_by:
                        summary_parts.append(f"  • Resolution due by {ticket_due_by}")
                else:
                    summary_parts.append(f"  • No conversations yet - initial response needed")
            else:
                summary_parts.append(f"  • Ticket is {ticket_status} - review for closure or follow-up")
            
            full_summary = "\n".join(summary_parts)
            
            return {
                "ticket_id": ticket_id,
                "summary": full_summary,
                "ticket_details": {
                    "subject": ticket_subject,
                    "status": ticket_status,
                    "priority": ticket_priority,
                    "type": ticket_type,
                    "created_at": ticket_created,
                    "updated_at": ticket_updated,
                    "due_by": ticket_due_by,
                    "fr_due_by": ticket_fr_due_by,
                    "requester_id": requester_id,
                    "responder_id": responder_id,
                    "group_id": group_id,
                    "tags": tags
                },
                "description": ticket_description,
                "conversations_summary": conversations_summary,
                "conversations_count": len(conversations),
                "escalation_indicators": len(escalation_indicators),
                "similar_tickets": similar_tickets_data,
                "raw_ticket": ticket
            }
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_json = e.response.json()
                if isinstance(error_json, dict):
                    description = error_json.get('description', '')
                    errors = error_json.get('errors', [])
                    if errors:
                        error_details = []
                        for err in errors:
                            if isinstance(err, dict):
                                error_details.append(f"{err.get('field', '')}: {err.get('message', '')}")
                            else:
                                error_details.append(str(err))
                        error_msg += f": {description}. Errors: {', '.join(error_details)}"
                    else:
                        error_msg += f": {description or e.response.text[:200]}"
                else:
                    error_msg += f": {e.response.text[:200]}"
            except:
                error_msg += f": {e.response.text[:500]}"
            return {"error": error_msg}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


@mcp.tool(name="find-similar-tickets-using-ai")
async def find_similar_tickets_using_ai(ticket_id: int) -> Dict[str, Any]:
    """Find similar tickets using Freshdesk AI.

    This tool uses the Copilot API to find tickets similar to the given ticket ID.
    It returns tickets with AI-generated summaries, resolution details, and confidence scores.

    Use this tool for queries like:
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

    Args:
        ticket_id: The ID of the ticket to find similar tickets for

    Returns:
        Dictionary with similar_tickets array containing:

    Example:
        # Find similar tickets for ticket 12345
        result = await find_similar_tickets_using_ai(ticket_id=12345)
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


@mcp.tool(name="add-ticket-reply")
async def add_ticket_reply(ticket_id: int, body: str = "Acknowledged. we are looking into the issue") -> Dict[str, Any]:
    """Add a reply to a ticket.
    
    This tool adds a reply/response to a specific ticket using the Freshdesk API.
    
    Use this tool for queries like:
    - "reply to ticket 12345 with message"
    - "add response to ticket 12345"
    - "respond to ticket 12345"
    - "send reply to ticket 12345"
    - "first response to ticket 12345"
    - "send first response to ticket 12345"
    - "add first response to ticket 12345"
    - "provide first response to ticket 12345"
    - "acknowledge ticket 12345"
    - "acknowledge ticket 12345 with first response"
    - "send acknowledgment to ticket 12345"
    - "first response for ticket 12345"
    - "first response"
    - "send response to ticket 12345"
    - "add response to ticket 12345"
    - "provide response to ticket 12345"
    - "provide reply to ticket 12345"
    - "reply to ticket 12345"
    - "reply"
    
    Args:
        ticket_id: The ticket ID to reply to (required)
        body: The reply message text (optional, defaults to "Acknowledged. we are looking into the issue")
    
    Returns:
        Dictionary with body_text if successful, or error message if failed
    
    Example:
        # Add a reply to ticket 12345 with default message
        result = await add_ticket_reply(ticket_id=12345)
        
        # Add a custom reply to ticket 12345
        result = await add_ticket_reply(ticket_id=12345, body="We are working on this issue. Will keep you posted.")
    """
    if not ticket_id or ticket_id < 1:
        return {"error": "Invalid ticket_id. Must be a positive integer."}
    
    if not body or not body.strip():
        return {"error": "Body parameter cannot be empty."}
    
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}/reply"
    headers = _get_auth_headers()
    
    # Prepare request payload
    payload = {
        "body": body.strip()
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.post(url, headers=headers, auth=_get_auth(), json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            # Check if body_text exists in response
            if isinstance(response_data, dict) and "body_text" in response_data:
                return {"body_text": response_data["body_text"]}
            else:
                return {"error": f"Unexpected response format. Expected body_text, got: {response_data}"}
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_json = e.response.json()
                if isinstance(error_json, dict):
                    description = error_json.get('description', '')
                    errors = error_json.get('errors', [])
                    if errors:
                        error_details = []
                        for err in errors:
                            if isinstance(err, dict):
                                error_details.append(f"{err.get('field', '')}: {err.get('message', '')}")
                            else:
                                error_details.append(str(err))
                        error_msg += f": {description}. Errors: {', '.join(error_details)}"
                    else:
                        error_msg += f": {description or e.response.text[:200]}"
                else:
                    error_msg += f": {e.response.text[:200]}"
            except:
                error_msg += f": {e.response.text[:500]}"
            return {"error": error_msg}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


def _format_date(date_str: str) -> str:
    """Convert ISO date string to readable format like 'Oct 14, 2025 10:45 AM'."""
    if not date_str:
        return ""
    try:
        # Parse ISO format date (e.g., "2025-10-14T10:45:53Z" or "2025-10-14T10:45:53")
        # Remove 'Z' timezone indicator and parse
        date_clean = date_str.replace('Z', '').split('.')[0]  # Remove Z and microseconds if present
        # Try parsing with different formats
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(date_clean, fmt)
                # Format as "Oct 14, 2025 10:45 AM" (12-hour format with AM/PM)
                if fmt == "%Y-%m-%d":
                    # Date only, no time
                    return dt.strftime("%b %d, %Y")
                else:
                    # Date and time
                    return dt.strftime("%b %d, %Y %I:%M %p")
            except ValueError:
                continue
        # If all formats fail, return original
        return date_str
    except (ValueError, AttributeError, TypeError):
        # If parsing fails, return original string
        return date_str


def _format_tickets_table(tickets: List[Dict[str, Any]]) -> str:
    """Format tickets as a table string."""
    if not tickets:
        return "No tickets found."
    
    # Define column headers
    headers = ["Ticket ID", "Subject", "Status", "Priority", "Resolution Due By", "First Response Due By"]
    
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    
    # Process tickets and calculate widths
    rows = []
    for ticket in tickets:
        ticket_id = str(ticket.get("ticket id", ""))
        subject = str(ticket.get("subject", "No subject"))[:50]  # Truncate long subjects
        status = str(ticket.get("status", ""))
        priority = str(ticket.get("priority", ""))
        resolution_due_by = _format_date(ticket.get("resolution_due_by", "")) if ticket.get("resolution_due_by") else ""
        fr_due_by = _format_date(ticket.get("first_response_due_by", "")) if ticket.get("first_response_due_by") else ""
        
        row = [ticket_id, subject, status, priority, resolution_due_by, fr_due_by]
        rows.append(row)
        
        # Update column widths - ensure we use the actual string length
        for i, value in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(value)))
    
    # Build table
    table_lines = []
    
    # Helper function to format a row
    def format_row(values):
        return " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(values))
    
    # Header row
    header_row = format_row(headers)
    table_lines.append(header_row)
    
    # Separator row - use dashes for each column width plus separators
    separator_parts = []
    for i, width in enumerate(col_widths):
        separator_parts.append("-" * width)
    separator_row = "-+-".join(separator_parts)
    table_lines.append(separator_row)
    
    # Data rows
    for row in rows:
        data_row = format_row(row)
        table_lines.append(data_row)
    
    return "\n".join(table_lines)


@mcp.tool(name="my-unresolved-tickets")
async def my_unresolved_tickets() -> Dict[str, Any]:
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

    Returns:
        Dictionary with tickets and pagination information

    Example:
        # Get my unresolved tickets using v2 API
        result = await my_unresolved_tickets()
    """
    # Get current user's agent ID from API
    agent_id = await _get_current_agent_id()
    
    if agent_id is None:
        return {"error": "Could not get agent ID from API. Please check your authentication."}

    # Build raw Freshdesk query (NO ENCODING EXCEPT SPACES → +)
    query = f"agent_id:{agent_id} AND (status:2 OR status:3 OR status:>6)"
    query = query.replace(" ", "+")  # Freshdesk wants + instead of spaces

    # Manually assemble URL with raw query
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/search/tickets?query=\"{query}\""
    headers = _get_auth_headers()
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, auth=_get_auth())
            response.raise_for_status()
            response_data = response.json()

            # Extract tickets from results key (API returns {"results": [...], "total": N})
            if not isinstance(response_data, dict):
                return {"error": f"Unexpected response format. Expected dict, got {type(response_data).__name__}"}
            
            tickets = response_data.get("results", [])
            total = response_data.get("total", len(tickets))
            
            if not isinstance(tickets, list):
                return {"error": f"Expected 'results' to be a list, got {type(tickets).__name__}"}

            # Format tickets with URLs and readable structure
            formatted_tickets = []
            for ticket in tickets:
                # Ensure ticket is a dict before accessing it
                if not isinstance(ticket, dict):
                    logging.warning(f"Skipping invalid ticket (not a dict): {type(ticket).__name__}")
                    continue
                    
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
            readable_summary = f"Found {total} unresolved ticket(s) assigned to you:"
            
            # Format tickets as table
            table_format = _format_tickets_table(formatted_tickets)

            return {
                "summary": readable_summary,
                "ticket_count": total,
                "tickets": formatted_tickets,
                "table": table_format,
                "pagination": {
                    "current_page": 1,
                    "total": total
                },
                "raw_tickets": tickets
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_json = e.response.json()
                if isinstance(error_json, dict):
                    description = error_json.get('description', '')
                    errors = error_json.get('errors', [])
                    if errors:
                        error_details = []
                        for err in errors:
                            if isinstance(err, dict):
                                error_details.append(f"{err.get('field', '')}: {err.get('message', '')}")
                            else:
                                error_details.append(str(err))
                        error_msg += f": {description}. Errors: {', '.join(error_details)}"
                    else:
                        error_msg += f": {description or e.response.text[:200]}"
                else:
                    error_msg += f": {e.response.text[:200]}"
            except:
                error_msg += f": {e.response.text[:500]}"
            return {"error": error_msg}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


def _normalize_squad_name(squad_name: str) -> str:
    """Normalize squad name for comparison by removing periods and converting to lowercase.
    
    Examples:
        "S.H.I.E.L.D" -> "shield"
        "shield" -> "shield"
        "Dracarys" -> "dracarys"
    """
    return str(squad_name).strip().replace(".", "").lower()


async def _validate_squad_name(squad_name: str) -> Dict[str, Any]:
    """Validate squad_name against L2 Teams choices from freshservice_teams field.
    
    The validation is case-insensitive and ignores periods, so "shield" will match "S.H.I.E.L.D".
    
    Args:
        squad_name: The squad name to validate
        
    Returns:
        Dictionary with "valid" (bool) and "error" (str) or "available_squads" (list)
    """
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/ticket_fields"
    headers = _get_auth_headers()
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, auth=_get_auth())
            response.raise_for_status()
            ticket_fields = response.json()
            
            if not isinstance(ticket_fields, list):
                return {"valid": False, "error": "Unexpected ticket fields response format"}
            
            # Find the freshservice_teams field
            freshservice_teams_field = None
            for field in ticket_fields:
                if isinstance(field, dict) and field.get("name") == "freshservice_teams":
                    freshservice_teams_field = field
                    break
            
            if not freshservice_teams_field:
                return {"valid": False, "error": "Could not find freshservice_teams field in ticket fields"}
            
            # Extract L2 Teams choices
            choices = freshservice_teams_field.get("choices", {})
            if not isinstance(choices, dict):
                return {"valid": False, "error": "freshservice_teams field does not have choices"}
            
            l2_teams = choices.get("L2 Teams")
            if l2_teams is None:
                return {"valid": False, "error": "L2 Teams choices not found in freshservice_teams field"}
            
            # Normalize the input squad name (remove periods, lowercase)
            squad_name_normalized = _normalize_squad_name(squad_name)
            available_squads = []
            matched_squad_name = None
            partial_matches = []
            
            if isinstance(l2_teams, list):
                # If it's a list, extract squad names directly
                available_squads = [str(choice).strip() for choice in l2_teams if choice]
                # First try exact normalized match (case-insensitive, ignores periods)
                for squad in available_squads:
                    squad_normalized = _normalize_squad_name(squad)
                    if squad_normalized == squad_name_normalized:
                        matched_squad_name = squad
                        break
                    # If no exact match, try partial matching
                    elif squad_name_normalized in squad_normalized or squad_normalized in squad_name_normalized:
                        partial_matches.append(squad)
            elif isinstance(l2_teams, dict):
                # If it's a dict, extract keys (squad names) - structure: {"Dracarys": ["ITPM"], "S.H.I.E.L.D": [...], ...}
                available_squads = [str(key).strip() for key in l2_teams.keys() if key]
                # First try exact normalized match against dict keys (case-insensitive, ignores periods)
                for squad_key in l2_teams.keys():
                    squad_key_str = str(squad_key).strip()
                    squad_normalized = _normalize_squad_name(squad_key_str)
                    if squad_normalized == squad_name_normalized:
                        matched_squad_name = squad_key_str
                        break
                    # If no exact match, try partial matching
                    elif squad_name_normalized in squad_normalized or squad_normalized in squad_name_normalized:
                        partial_matches.append(squad_key_str)
            else:
                return {"valid": False, "error": "L2 Teams choices have invalid format (expected list or dict)"}
            
            # If exact match found, return it
            if matched_squad_name:
                return {"valid": True, "matched_squad_name": matched_squad_name}
            
            # If partial matches found, handle them
            if partial_matches:
                if len(partial_matches) == 1:
                    # Single partial match - use it
                    return {"valid": True, "matched_squad_name": partial_matches[0]}
                else:
                    # Multiple partial matches - return error with suggestions
                    return {
                        "valid": False,
                        "error": f"Squad name '{squad_name}' partially matches multiple squads. Please be more specific.",
                        "partial_matches": partial_matches,
                        "available_squads": available_squads
                    }
            
            # No match found
            return {
                "valid": False,
                "error": f"Squad name '{squad_name}' not found in L2 Teams",
                "available_squads": available_squads
            }
                
        except httpx.HTTPStatusError as e:
            return {"valid": False, "error": f"Failed to fetch ticket fields: HTTP {e.response.status_code}"}
        except Exception as e:
            return {"valid": False, "error": f"An unexpected error occurred: {str(e)}"}


async def get_all_unresolved_tickets_in_a_squad(squad_name: str) -> Dict[str, Any]:
    """Get all unresolved tickets in a squad.
    
    This tool fetches unresolved tickets for a specific squad by filtering tickets
    where the team_member custom field matches the squad name.
    
    The squad_name is validated against the L2 Teams choices from the freshservice_teams
    field in the ticket fields API.
    
    Use this tool for queries like:
    - "unresolved tickets in Dracarys squad"
    - "tickets for squad Dracarys"
    - "all open tickets in my squad"
    - "squad tickets"
    
    Args:
        squad_name: The squad name to filter by (required). This matches the team_member custom field.
                   Must be a valid L2 Teams choice from freshservice_teams field.
    
    Returns:
        Dictionary with filtered tickets list
    
    Example:
        # Get unresolved tickets for Dracarys squad
        result = await get_all_unresolved_tickets_in_a_squad(squad_name="Dracarys")
    """
    if not squad_name:
        return {"error": "squad_name parameter is required"}
    
    # Validate squad_name against L2 Teams choices
    validation_result = await _validate_squad_name(squad_name)
    if not validation_result.get("valid", False):
        error_msg = validation_result.get("error", "Invalid squad name")
        
        # Show partial matches if they exist (for multiple matches case)
        partial_matches = validation_result.get("partial_matches")
        if partial_matches:
            error_msg += f" Found {len(partial_matches)} partial match(es): {', '.join(partial_matches[:10])}"
            if len(partial_matches) > 10:
                error_msg += f" (and {len(partial_matches) - 10} more)"
            error_msg += ". Please use one of these exact squad names."
        
        # Show available squads only if no partial matches were found
        available_squads = validation_result.get("available_squads")
        if available_squads and not partial_matches:
            error_msg += f" Available squads: {', '.join(available_squads[:10])}"  # Show first 10
            if len(available_squads) > 10:
                error_msg += f" (and {len(available_squads) - 10} more)"
        
        return {"error": error_msg}
    
    # Use the matched squad name from validation (exact case from API)
    matched_squad_name = validation_result.get("matched_squad_name", squad_name)
    
    # Build raw Freshdesk query (NO ENCODING EXCEPT SPACES → +)
    query = "bu:'Freshservice' AND (status:2 OR status:3 OR status:>6) AND type:'L3 - Developer Assistance'"
    query = query.replace(" ", "+")  # Freshdesk wants + instead of spaces
    
    # Manually assemble URL with raw query
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/search/tickets?query=\"{query}\""
    headers = _get_auth_headers()
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, auth=_get_auth())
            response.raise_for_status()
            response_data = response.json()
            
            # Extract tickets from results key (API returns {"results": [...], "total": N})
            if not isinstance(response_data, dict):
                return {"error": f"Unexpected response format. Expected dict, got {type(response_data).__name__}"}
            
            all_tickets = response_data.get("results", [])
            total_before_filter = response_data.get("total", len(all_tickets))
            
            if not isinstance(all_tickets, list):
                return {"error": f"Expected 'results' to be a list, got {type(all_tickets).__name__}"}
            
            # Filter tickets where team_member custom field matches matched_squad_name
            filtered_tickets = []
            for ticket in all_tickets:
                if not isinstance(ticket, dict):
                    logging.warning(f"Skipping invalid ticket (not a dict): {type(ticket).__name__}")
                    continue
                
                # Check custom_fields for team_member
                custom_fields = ticket.get("custom_fields", {})
                if not isinstance(custom_fields, dict):
                    continue
                
                team_member = custom_fields.get("team_member")
                # Handle null, None, empty string, or missing values
                if team_member is None or team_member == "":
                    continue
                
                # Compare team_member with matched_squad_name (case-sensitive, trimmed)
                if str(team_member).strip() == str(matched_squad_name).strip():
                    filtered_tickets.append(ticket)
            
            # Format filtered tickets with URLs and readable structure
            formatted_tickets = []
            for ticket in filtered_tickets:
                ticket_id = ticket.get("id")
                ticket_url = f"https://{FRESHDESK_DOMAIN}/a/tickets/{ticket_id}"
                
                status_id = ticket.get("status")
                priority_id = ticket.get("priority")
                custom_fields = ticket.get("custom_fields", {})
                
                # Get team_member, handling null/None values
                team_member_value = ""
                if isinstance(custom_fields, dict):
                    team_member_value = custom_fields.get("team_member") or ""
                
                formatted_ticket = {
                    "ticket id": ticket_id,
                    "url": ticket_url,
                    "subject": ticket.get("subject", "No subject"),
                    "status": _get_status_name(status_id),
                    "priority": _get_priority_name(priority_id),
                    "squad": matched_squad_name,
                    "resolution_due_by": ticket.get("due_by", ""),
                    "team_member": team_member_value
                }
                
                # Only include fr_due_by if it exists
                if ticket.get("fr_due_by"):
                    formatted_ticket["first_response_due_by"] = ticket.get("fr_due_by")
                    
                formatted_tickets.append(formatted_ticket)
            
            # Build readable summary using matched_squad_name
            readable_summary = f"Found {len(formatted_tickets)} unresolved ticket(s) in squad '{matched_squad_name}' (filtered from {total_before_filter} total tickets):"
            
            # Format tickets as table
            table_format = _format_tickets_table(formatted_tickets)
            
            return {
                "summary": readable_summary,
                "squad_name": matched_squad_name,
                "original_squad_name": squad_name,
                "ticket_count": len(formatted_tickets),
                "total_before_filter": total_before_filter,
                "tickets": formatted_tickets,
                "table": table_format,
                "pagination": {
                    "current_page": 1,
                    "total": len(formatted_tickets)
                },
                "raw_tickets": filtered_tickets
            }
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_json = e.response.json()
                if isinstance(error_json, dict):
                    description = error_json.get('description', '')
                    errors = error_json.get('errors', [])
                    if errors:
                        error_details = []
                        for err in errors:
                            if isinstance(err, dict):
                                error_details.append(f"{err.get('field', '')}: {err.get('message', '')}")
                            else:
                                error_details.append(str(err))
                        error_msg += f": {description}. Errors: {', '.join(error_details)}"
                    else:
                        error_msg += f": {description or e.response.text[:200]}"
                else:
                    error_msg += f": {e.response.text[:200]}"
            except:
                error_msg += f": {e.response.text[:500]}"
            return {"error": error_msg}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


async def get_ticket_conversations(ticket_id: int) -> Dict[str, Any]:
    """Get all conversations for a ticket.
    
    This tool fetches all conversations (notes, replies, etc.) for a specific ticket
    and provides a minimal summary of the conversation thread.
    
    Use this tool for queries like:
    - "show conversations for ticket 12345"
    - "get notes for ticket 12345"
    - "list all messages in ticket 12345"
    - "ticket 12345 conversations"
    
    Args:
        ticket_id: The ticket ID to get conversations for (required)
    
    Returns:
        Dictionary with conversations list and summary
    
    Example:
        # Get conversations for ticket 18963595
        result = await get_ticket_conversations(ticket_id=18963595)
    """
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}/conversations"
    headers = _get_auth_headers()
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, headers=headers, auth=_get_auth())
            response.raise_for_status()
            conversations = response.json()
            
            if not isinstance(conversations, list):
                return {"error": f"Unexpected response format. Expected list, got {type(conversations).__name__}"}
            
            # Format conversations
            formatted_conversations = []
            for conv in conversations:
                if not isinstance(conv, dict):
                    continue
                
                formatted_conv = {
                    "id": conv.get("id"),
                    "created_at": _format_date(conv.get("created_at", "")),
                    "incoming": conv.get("incoming", False),
                    "private": conv.get("private", False),
                    "body_text": conv.get("body_text", "")[:200] + "..." if len(conv.get("body_text", "")) > 200 else conv.get("body_text", ""),
                    "user_id": conv.get("user_id"),
                    "attachments": len(conv.get("attachments", [])) if conv.get("attachments") else 0
                }
                formatted_conversations.append(formatted_conv)
            
            # Create minimal summary
            total_conversations = len(formatted_conversations)
            public_count = sum(1 for c in formatted_conversations if not c.get("private", True))
            private_count = total_conversations - public_count
            incoming_count = sum(1 for c in formatted_conversations if c.get("incoming", False))
            outgoing_count = total_conversations - incoming_count
            total_attachments = sum(c.get("attachments", 0) for c in formatted_conversations)
            
            # Get first and last conversation dates
            first_date = formatted_conversations[0].get("created_at", "") if formatted_conversations else ""
            last_date = formatted_conversations[-1].get("created_at", "") if formatted_conversations else ""
            
            summary = (
                f"Ticket #{ticket_id} has {total_conversations} conversation(s). "
                f"Public: {public_count}, Private: {private_count}. "
                f"Incoming: {incoming_count}, Outgoing: {outgoing_count}. "
                f"Attachments: {total_attachments}. "
                f"First: {first_date}, Last: {last_date}"
            )
            
            return {
                "ticket_id": ticket_id,
                "summary": summary,
                "total_conversations": total_conversations,
                "conversations": formatted_conversations,
                "raw_conversations": conversations
            }
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_json = e.response.json()
                if isinstance(error_json, dict):
                    description = error_json.get('description', '')
                    errors = error_json.get('errors', [])
                    if errors:
                        error_details = []
                        for err in errors:
                            if isinstance(err, dict):
                                error_details.append(f"{err.get('field', '')}: {err.get('message', '')}")
                            else:
                                error_details.append(str(err))
                        error_msg += f": {description}. Errors: {', '.join(error_details)}"
                    else:
                        error_msg += f": {description or e.response.text[:200]}"
                else:
                    error_msg += f": {e.response.text[:200]}"
            except:
                error_msg += f": {e.response.text[:500]}"
            return {"error": error_msg}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}


async def get_all_unresolved_tickets_in_a_squad_old(
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
        result = await get_all_unresolved_tickets_in_a_squad_old(squad="Dracarys")
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

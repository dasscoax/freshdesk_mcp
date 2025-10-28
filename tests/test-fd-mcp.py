import asyncio
from freshdesk_mcp.server import get_ticket, get_tickets, search_tickets, search_agents, filter_tickets, get_unresolved_tickets, get_current_agent_id, get_unresolved_tickets_by_squad


async def test_get_ticket():
    ticket_id = 1289  # Replace with a test ticket ID
    result = await get_ticket(ticket_id)
    print(result)


async def test_get_tickets():
    page = 1
    per_page = 30
    result = await get_tickets(page, per_page)
    print(result)


async def test_search_tickets():
    query = "status:open"  # Replace with a test query
    result = await search_tickets(query)
    print(result)


async def test_search_agents():
    query = "john"  # Replace with a test query
    result = await search_agents(query)
    print(result)


async def test_filter_tickets_by_assignee():
    """Test filtering tickets by assignee name"""
    # Replace with actual assignee name or email
    assignee_name = "John Doe"  # Replace with actual assignee name
    result = await filter_tickets(assignee_name=assignee_name)
    print(result)


async def test_filter_tickets_by_query_hash():
    """Test filtering tickets using query_hash format"""
    query_hash = [
        {
            "condition": "responder_id",
            "operator": "is_in",
            "type": "default",
            "value": [50000560730]  # Replace with actual agent ID
        },
        {
            "condition": "status",
            "operator": "is_in",
            "type": "default",
            "value": [2]  # Open status
        }
    ]
    result = await filter_tickets(query_hash=query_hash)
    print(result)


async def test_filter_tickets_by_status():
    """Test filtering tickets by status"""
    result = await filter_tickets(status=2)  # Open status
    print(result)


async def test_filter_tickets_with_custom_fields():
    """Test filtering tickets with custom fields (freshservice_teams, team_member, cf_request_for)"""
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
        },
        {
            "condition": "status",
            "operator": "is_in",
            "type": "default",
            "value": [0]  # New status
        },
        {
            "condition": "responder_id",
            "operator": "is_in",
            "type": "default",
            "value": [50000560730]
        }
    ]
    result = await filter_tickets(query_hash=query_hash)
    print(result)


async def test_get_unresolved_tickets():
    """Test getting unresolved tickets assigned to an agent"""
    # Replace with actual assignee name, email, or ID
    assignee_id = 50000560730  # Replace with actual agent ID
    result = await get_unresolved_tickets(assignee_id=assignee_id)
    print(result)


async def test_get_unresolved_tickets_by_name():
    """Test getting unresolved tickets by assignee name"""
    # Replace with actual assignee name or email
    assignee_name = "John Doe"  # Replace with actual assignee name
    result = await get_unresolved_tickets(assignee_name=assignee_name)
    print(result)


async def test_get_unresolved_tickets_all_statuses():
    """Test getting unresolved tickets with all status types"""
    # Get both Open and Pending tickets
    assignee_id = 50000560730  # Replace with actual agent ID
    result = await get_unresolved_tickets(assignee_id=assignee_id, status=[2, 3])
    print(result)


async def test_get_unresolved_tickets_current_user():
    """Test getting unresolved tickets for current user"""
    result = await get_unresolved_tickets(use_current_user=True)
    print(result)


async def test_get_current_agent_id():
    """Test getting current agent ID"""
    result = await get_current_agent_id()
    print(result)


async def test_get_unresolved_tickets_by_squad():
    """Test getting unresolved tickets by squad"""
    result = await get_unresolved_tickets_by_squad(squad="Dracarys")
    print(result)


async def test_get_unresolved_tickets_by_squad_with_status():
    """Test getting unresolved tickets by squad with different status"""
    result = await get_unresolved_tickets_by_squad(
        squad="Dracarys",
        status="open"
    )
    print(result)


if __name__ == "__main__":
    pass  # Uncomment the test functions below to run them
    # asyncio.run(test_get_ticket())
    # asyncio.run(test_get_tickets())
    # asyncio.run(test_search_tickets())
    # asyncio.run(test_search_agents())
    # asyncio.run(test_filter_tickets_by_assignee())
    # asyncio.run(test_filter_tickets_by_query_hash())
    # asyncio.run(test_filter_tickets_by_status())
    # asyncio.run(test_filter_tickets_with_custom_fields())
    # asyncio.run(test_get_unresolved_tickets())
    # asyncio.run(test_get_unresolved_tickets_by_name())
    # asyncio.run(test_get_unresolved_tickets_all_statuses())
    # asyncio.run(test_get_unresolved_tickets_current_user())
    # asyncio.run(test_get_current_agent_id())
    # asyncio.run(test_get_unresolved_tickets_by_squad())
    # asyncio.run(test_get_unresolved_tickets_by_squad_with_pagination())

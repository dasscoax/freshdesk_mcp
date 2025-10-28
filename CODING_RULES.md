# Coding Rules for Freshdesk MCP

## General Principles

### 1. Don't Assume Anything for API and Response Structure
- **Never assume**: Always verify API endpoint structure, request parameters, and response formats
- **Use exact specifications**: When provided, use the exact API structure (e.g., query_hash format)
- **Validate responses**: Always check for errors in API responses before processing
- **Document assumptions**: If you must make assumptions, document them clearly in code comments

### 2. Create Optimized Code
- **Avoid duplication**: Reuse helper functions instead of repeating code
- **Efficient API calls**: Minimize API calls by batching when possible
- **Error handling**: Implement proper error handling with clear error messages
- **Resource management**: Use async context managers properly
- **Caching**: Consider caching for frequently accessed data (like agent IDs, field definitions)

### 3. Fix All Indentation Errors and Avoid Any Indentation Errors
- **Consistent indentation**: Use 4 spaces (no tabs) throughout the codebase
- **Block structure**: Ensure try-except, if-else, and function blocks are properly indented
- **Line continuation**: Use proper indentation for multi-line statements
- **Verify before commit**: Always check for indentation errors before committing

### 4. Compile server.py File for Any Lint and Indentation Errors
- **Pre-commit checks**: Run linting before committing code
- **Python syntax**: Validate using `python -m py_compile src/freshdesk_mcp/server.py`
- **Linter**: Use a linter (pylint, ruff, etc.) to catch errors
- **No warnings**: Fix all linter warnings before considering code complete
- **Type hints**: Use proper type hints for function parameters and return types

## Specific Rules

### API Implementation
```python
# ✅ Good: Validates response structure
async def get_agent():
    response = await client.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    if "agent" in data and "id" in data["agent"]:
        return data["agent"]["id"]
    return None

# ❌ Bad: Assumes response structure
async def get_agent():
    response = await client.get(url, headers=headers)
    return response.json()["agent"]["id"]  # Could fail
```

### Indentation
```python
# ✅ Good: Proper indentation
async def function():
    if condition:
        try:
            response = await api_call()
            return response.json()
        except Exception as e:
            logging.error(str(e))
            return None

# ❌ Bad: Inconsistent indentation
async def function():
    if condition:
     try:
    response = await api_call()  # Wrong indentation
      return response.json()
    except Exception as e:
     logging.error(str(e))
```

### Error Handling
```python
# ✅ Good: Comprehensive error handling
async def api_call():
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logging.error(f"HTTP error: {e}")
        return {"error": f"API error: {str(e)}"}
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {"error": f"Unexpected error: {str(e)}"}

# ❌ Bad: No error handling
async def api_call():
    response = await client.get(url)
    return response.json()  # Could raise exception
```

## Workflow

1. **Write code** following these rules
2. **Check syntax**: `python -m py_compile src/freshdesk_mcp/server.py`
3. **Run linter**: Fix all warnings and errors
4. **Test**: Verify the functionality works as expected
5. **Commit**: Only after all checks pass

## Tools

- **Syntax check**: `python -m py_compile`
- **Linter**: Use IDE built-in linter or `ruff check`
- **Type checking**: `mypy` (optional)
- **Auto-format**: `black` or `ruff format`


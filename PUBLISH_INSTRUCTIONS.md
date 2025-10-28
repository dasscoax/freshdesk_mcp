# Publishing to PyPI

## Current Status
✅ Package built successfully
- Source distribution: `freshdesk_mcp-1.0.0.tar.gz`
- Wheel: `freshdesk_mcp-1.0.0-py3-none-any.whl`

## To Publish

### Option 1: Using uv with API token
```bash
# Get your PyPI API token from https://pypi.org/manage/account/token/
uv publish --token pypi-YOUR_TOKEN_HERE
```

### Option 2: Using twine
```bash
# Install twine if not already installed
uv pip install twine

# Publish (will prompt for credentials)
twine upload dist/*

# Or with credentials inline
twine upload dist/* --username YOUR_USERNAME --password YOUR_TOKEN
```

### Option 3: Configure credentials
```bash
# Create ~/.pypirc file
cat > ~/.pypirc << EOF
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
EOF

# Then run
uv publish
```

### Option 4: Test on TestPyPI first
```bash
# Use TestPyPI for testing
uv publish --index-url https://test.pypi.org/simple/
```

## After Publishing

Install your package from PyPI:
```bash
pip install freshdesk-mcp
```

Run it:
```bash
freshdesk-mcp
```

## Notes
- Ensure version number is updated in `pyproject.toml` before publishing new versions
- API tokens should be kept secure and never committed to version control
- Test on TestPyPI first before publishing to production PyPI


# FastMCP Cloud Setup (Concise)

## 1. Environment Variables (Set in FastMCP Cloud UI)

```text
# Required - Database
FALKORDB_URI=redis://your-cloud-instance:port
FALKORDB_DATABASE=default_db
FALKORDB_USER=your_username
FALKORDB_PASSWORD=your_password

# Required - LLM
OPENAI_API_KEY=your_openai_key

# Required - Security (Authentication)
GRAPHITI_AUTH_ENABLED=true
GRAPHITI_API_KEY_ADMIN=sk_admin_<generated_32_char_token>
GRAPHITI_API_KEY_READONLY=sk_readonly_<generated_32_char_token>
GRAPHITI_API_KEY_ANALYST=sk_analyst_<generated_32_char_token>

# Required - Security (Authorization)
EUNOMIA_POLICY_FILE=config/mcp_policies.json
```

## 2. Deploy Configuration

- Repository: Connect your GitHub repo
- Entrypoint: src/server.py:create_server ⚠️ (NOT src/graphiti_mcp_server.py:mcp)
- Branch: main (auto-deploys on push)

## 3. Generate API Keys Before Deploy

```bash
python3 -c "import secrets; print(f'sk_admin_{secrets.token_urlsafe(32)}')"
python3 -c "import secrets; print(f'sk_readonly_{secrets.token_urlsafe(32)}')"
python3 -c "import secrets; print(f'sk_analyst_{secrets.token_urlsafe(32)}')"
```

Copy these into FastMCP Cloud environment variables.

## 4. What FastMCP Handles Automatically

- HTTPS/SSL certificates
- pyproject.toml dependency installation
- Environment variable interpolation with ${VAR} syntax
- Auto-restart on config changes
- Preview deployments for PRs

Note: config/mcp_policies.json must be committed to git (it contains no secrets).
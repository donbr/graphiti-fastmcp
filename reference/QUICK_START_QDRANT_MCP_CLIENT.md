# Quick Start Client Guide: Using the Qdrant MCP Server

**For Users:** This guide shows you how to use the `qdrant-docs` MCP server in Claude Code, including available tools, sample queries, and best practices.

---

## Available MCP Tools

The `qdrant-docs` server provides **2 tools** for semantic documentation search:

### 1. `search_docs` - Semantic Documentation Search

**What it does:** Searches 2,670 documentation pages using semantic similarity (AI-powered understanding, not just keywords).

**Parameters:**
- `query` (required): Natural language question or topic
- `k` (optional): Number of results (default: 5, max: 20)
- `source` (optional): Filter by documentation source

**Available Sources:**
- `Anthropic` (932 pages)
- `LangChain` (506 pages)
- `Prefect` (767 pages)
- `FastMCP` (175 pages)
- `McpProtocol` (44 pages)
- `PydanticAI` (127 pages)
- `Zep` (119 pages)

---

### 2. `list_sources` - View Available Documentation

**What it does:** Shows all available documentation sources and page counts.

**Parameters:** None

---

## How to Use (Sample Queries)

### Basic Documentation Search

**What to ask:**
> "Search for documentation about building RAG agents"

**What Claude Code does:**
```
Uses: search_docs("building RAG agents", k=5)
```

**What you get:**
- 5 most relevant documentation pages
- Title, source, URL for each result
- Content preview (first 1000 chars)
- Semantic ranking (most relevant first)

---

### Specific Technology Search

**What to ask:**
> "How does LangChain handle document loaders?"

**What Claude Code does:**
```
Uses: search_docs("document loaders", source="LangChain", k=5)
```

**What you get:**
- Results filtered to only LangChain documentation
- Most relevant pages about document loaders
- Direct links to official docs

---

### Comparative Search

**What to ask:**
> "What are the differences between LangChain and PydanticAI for building agents?"

**What Claude Code does:**
```
Uses: search_docs("building agents", source="LangChain", k=3)
Uses: search_docs("building agents", source="PydanticAI", k=3)
```

**What you get:**
- Relevant pages from both frameworks
- Side-by-side comparison from official docs
- Links to both documentation sets

---

### Implementation Guidance

**What to ask:**
> "Show me how to implement prompt caching in Anthropic's API"

**What Claude Code does:**
```
Uses: search_docs("prompt caching implementation", source="Anthropic", k=5)
```

**What you get:**
- Official Anthropic documentation on prompt caching
- Code examples (if available in docs)
- Best practices and configuration

---

### Troubleshooting Search

**What to ask:**
> "How do I fix connection errors with Qdrant Cloud?"

**What Claude Code does:**
```
Uses: search_docs("Qdrant connection errors troubleshooting", k=5)
```

**What you get:**
- Relevant troubleshooting documentation
- Common error solutions
- Configuration examples

---

### Explore Available Sources

**What to ask:**
> "What documentation sources are available?"

**What Claude Code does:**
```
Uses: list_sources()
```

**What you get:**
```
Available Documentation Sources:

Source          Documents
------------------------------
Anthropic       932
FastMCP         175
LangChain       506
McpProtocol     44
Prefect         767
PydanticAI      127
Zep             119
------------------------------
TOTAL           2670
```

---

## Sample Conversation Flows

### Flow 1: Learning a New Framework

**You:**
> "I want to learn about FastMCP. What documentation is available?"

**Claude Code:**
```
Uses: list_sources()
Response: Shows FastMCP has 175 documentation pages available
```

**You:**
> "Show me FastMCP documentation about creating MCP servers"

**Claude Code:**
```
Uses: search_docs("creating MCP servers", source="FastMCP", k=5)
Response: Returns 5 most relevant FastMCP pages with code examples
```

**You:**
> "How do I add environment variables to a FastMCP server?"

**Claude Code:**
```
Uses: search_docs("environment variables configuration", source="FastMCP", k=3)
Response: Returns specific documentation about env var configuration
```

---

### Flow 2: Solving a Specific Problem

**You:**
> "I'm getting rate limit errors when using OpenAI embeddings with Qdrant"

**Claude Code:**
```
Uses: search_docs("OpenAI rate limit errors embeddings", k=5)
Response: Returns documentation about rate limiting, batching, retry strategies
```

**You:**
> "Show me Anthropic's documentation about API rate limits"

**Claude Code:**
```
Uses: search_docs("API rate limits", source="Anthropic", k=3)
Response: Returns Anthropic-specific rate limit documentation
```

---

### Flow 3: Architecture Decision

**You:**
> "Should I use LangChain or PydanticAI for my RAG application?"

**Claude Code:**
```
Uses: search_docs("RAG application architecture", source="LangChain", k=3)
Uses: search_docs("RAG application architecture", source="PydanticAI", k=3)
Response: Compares approaches from both frameworks' official docs
```

**You:**
> "What does each framework say about retrieval strategies?"

**Claude Code:**
```
Uses: search_docs("retrieval strategies", source="LangChain", k=3)
Uses: search_docs("retrieval strategies", source="PydanticAI", k=3)
Response: Detailed comparison of retrieval approaches
```

---

## Advanced Query Patterns

### Pattern 1: Filtered Deep Dive

**Query:**
> "Find all Prefect documentation about workflow orchestration and error handling"

**Claude Code automatically:**
1. Searches with `source="Prefect"` filter
2. Retrieves top 5-10 results
3. Summarizes key concepts
4. Provides direct documentation links

---

### Pattern 2: Multi-Source Research

**Query:**
> "Compare how Anthropic, OpenAI, and LangChain handle streaming responses"

**Claude Code automatically:**
1. Searches each source independently
2. Extracts relevant sections
3. Compares approaches
4. Highlights differences

---

### Pattern 3: Example-Focused Search

**Query:**
> "Show me code examples for implementing Zep memory in a chatbot"

**Claude Code automatically:**
1. Searches Zep documentation for "memory chatbot implementation"
2. Prioritizes pages with code examples
3. Returns formatted code snippets
4. Provides context and explanations

---

## Understanding Search Results

### Result Format

Each search result includes:

```
================================================================================
Result 1/5
================================================================================
Title: [Page Title]
Source: [Source Name]
URL: [Direct Link to Documentation]
Doc ID: [Unique Identifier]

Content Preview (14395 chars total):
--------------------------------------------------------------------------------
[First 1000 characters of the documentation page...]

[Truncated. Full content: 14395 chars]
```

### What the Preview Shows

- **Title:** Original documentation page title
- **Source:** Which framework/product (e.g., "LangChain", "Anthropic")
- **URL:** Direct link to the original documentation
- **Content Preview:** First 1000 characters
- **Full Length:** Total characters available (useful for estimating reading time)

---

## Tips for Effective Searches

### ✅ DO: Use Natural Language

**Good:**
> "How do I set up authentication for MCP servers?"

**Why it works:** Semantic search understands concepts, not just keywords.

---

### ✅ DO: Be Specific

**Good:**
> "FastMCP environment variable configuration for production deployment"

**Better than:**
> "FastMCP config"

**Why it works:** More specific queries get more relevant results.

---

### ✅ DO: Use Source Filters

**Good:**
> "Show me Anthropic's documentation about Claude API models"

**Claude Code automatically adds:** `source="Anthropic"`

**Why it works:** Filters reduce noise, improve relevance.

---

### ✅ DO: Ask for Comparisons

**Good:**
> "What are the differences between LangChain vector stores and Qdrant direct integration?"

**Why it works:** Claude Code can search multiple sources and synthesize.

---

### ❌ DON'T: Use Only Keywords

**Avoid:**
> "API key env"

**Better:**
> "How do I configure API keys using environment variables?"

**Why:** Full questions get better semantic matches.

---

### ❌ DON'T: Request Information Not in Docs

**Avoid:**
> "What's the best restaurant near Qdrant headquarters?"

**Why:** The MCP server only has technical documentation, not general knowledge.

---

## Troubleshooting

### No Results Found

**Issue:**
```
No results found for query: 'XYZ'
```

**Solutions:**
1. Try a broader query
2. Check if you're searching the right source
3. Use `list_sources()` to verify source availability
4. Rephrase using different terminology

**Example:**
- ❌ "How to use agents in FastMCP"
- ✅ "Creating MCP servers with tools" (FastMCP uses "tools", not "agents")

---

### Wrong Source Results

**Issue:** Getting results from unexpected sources

**Solution:** Explicitly specify the source:
> "Show me **LangChain** documentation about [topic]"

Claude Code will add `source="LangChain"` automatically.

---

### Too Many/Too Few Results

**Adjust result count:**
- **Too many:** "Show me the **top 3** results for..."
- **Too few:** "Show me **10-15 results** for..."

Default is 5 results, max is 20.

---

## Performance Notes

- **Search Latency:** ~200-500ms per query (includes AI embedding generation)
- **Cost:** ~$0.0001 per search (OpenAI API)
- **Freshness:** Documentation was ingested on 2025-11-29
- **Coverage:** 2,670 pages across 7 major frameworks/platforms

---

## What's NOT Included

The MCP server does **not** have:

❌ General web search
❌ Real-time documentation updates
❌ Source code repositories
❌ Community forums/Stack Overflow
❌ Blog posts or tutorials (only official docs)

It **only** searches official documentation from:
- Anthropic
- LangChain
- Prefect
- FastMCP
- McpProtocol
- PydanticAI
- Zep

---

## Common Use Cases

### 1. Learning New Frameworks

**Workflow:**
1. List sources to see what's available
2. Search for "getting started" or "quickstart"
3. Deep dive into specific features
4. Find code examples

**Example queries:**
- "Show me PydanticAI getting started guide"
- "FastMCP tutorial for beginners"
- "LangChain basic RAG example"

---

### 2. API Reference Lookup

**Workflow:**
1. Search for specific API/function name
2. Filter by source if known
3. Review parameters and return types
4. Find usage examples

**Example queries:**
- "Anthropic Messages API parameters"
- "LangChain document loader API"
- "Prefect flow decorator options"

---

### 3. Troubleshooting Errors

**Workflow:**
1. Search for error message or symptom
2. Review common issues documentation
3. Find configuration examples
4. Check best practices

**Example queries:**
- "Qdrant connection timeout errors"
- "OpenAI rate limit handling"
- "LangChain memory serialization issues"

---

### 4. Architecture Planning

**Workflow:**
1. Compare approaches across frameworks
2. Review best practices documentation
3. Find architectural patterns
4. Evaluate trade-offs

**Example queries:**
- "Compare LangChain vs PydanticAI agent architectures"
- "Prefect workflow best practices for data pipelines"
- "Anthropic prompt engineering guidelines"

---

## Advanced Features

### Semantic Understanding

The search understands **concepts**, not just keywords:

**Query:** "How do I remember conversation history?"

**Understands as:**
- Memory management
- Conversation state
- Session persistence
- Chat history storage

**Returns:** Documentation about memory, state management, and persistence from relevant frameworks.

---

### Context-Aware Results

**Query:** "Show me authentication docs for MCP"

**Understands context:**
- MCP = Model Context Protocol
- Authentication = API keys, OAuth, tokens
- Relevant to: FastMCP, McpProtocol

**Filters intelligently** to MCP-related sources.

---

## Need Help?

### Getting Started
1. Try `list_sources()` to see what's available
2. Start with broad queries, then refine
3. Use source filters for targeted results

### Best Results
- Use natural language questions
- Be specific about what you need
- Specify the framework/source when known
- Ask for comparisons across frameworks

### If Stuck
- Check the source is available with `list_sources()`
- Try different phrasing
- Broaden your query
- Use fewer technical terms (search understands concepts)

---

## Quick Reference Card

| Task | Sample Query | Tool Used |
|------|-------------|-----------|
| List all sources | "What documentation is available?" | `list_sources()` |
| Basic search | "How do I build RAG agents?" | `search_docs(query, k=5)` |
| Filtered search | "Show me Anthropic docs about streaming" | `search_docs(query, source="Anthropic")` |
| More results | "Find 10 results about error handling" | `search_docs(query, k=10)` |
| Compare frameworks | "LangChain vs PydanticAI for agents" | Multiple `search_docs()` calls |
| Troubleshoot | "Qdrant connection errors" | `search_docs(error_message)` |
| API reference | "Prefect flow decorator parameters" | `search_docs(api_name, source)` |

---

**Ready to search?** Just ask Claude Code a question about any of the 7 supported frameworks, and it will automatically use the MCP server to find the most relevant documentation!

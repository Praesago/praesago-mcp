# praesago-mcp

A local MCP server for [Praesago](https://praesago.com): property and area data for every postcode district in **England and Wales**
(sold prices, rents, live listings statistics, planning, crime, schools, flood risk, broadband, council tax and more), for Claude,
Cursor and any other MCP client.

It is a small bridge with no dependencies. It runs on your machine over stdio and forwards each message to the hosted Praesago MCP
server at `https://praesago.com/api/mcp`. If your client can connect to a remote MCP server by URL, you can use that URL directly
and do not need this package (setup: https://praesago.com/docs/mcp).

## Install

```bash
pip install praesago-mcp
# or run it without installing:
uvx praesago-mcp
```

## Use with Claude Desktop

Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "praesago": {
      "command": "uvx",
      "args": ["praesago-mcp"],
      "env": { "PRAESAGO_API_KEY": "your-key (optional)" }
    }
  }
}
```

Other clients (Cursor, VS Code, Windsurf): use the command `praesago-mcp` (or `uvx praesago-mcp`) the same way.

## API key

Without a key the tools return headline facts for a limited number of calls a day. A key adds the full profile of each district.
Create one at https://praesago.com/developer and set it as `PRAESAGO_API_KEY`. The key is sent only to praesago.com, as the
`X-API-Key` header.

## Tools

The tools come from the hosted server, so they are always the current set. For example: `get_area_overview`, `get_area_context`,
`get_area_profile`, `compare_areas`, `search_areas`, `screen_areas`, `get_market_pulse`, `search` and `fetch`. Each area tool takes a
postcode (`E17 7AB`), a postcode district (`E17`) or a place name (`Walthamstow`). Full list: https://praesago.com/llms-full.txt

Example questions:

- "What is the median sold price in E17, and how did it change in a year?"
- "Compare Walthamstow and Leyton on crime and broadband."
- "Which districts in the North West have a median price under £150,000?"

## Coverage

England and Wales only. Scotland and Northern Ireland are not covered. Every figure comes from a named source and carries its date
or year. There are no forecasts and no valuations of single homes.

## Settings

| Variable | Meaning |
|---|---|
| `PRAESAGO_API_KEY` | Optional. Your Praesago API key. |
| `PRAESAGO_MCP_URL` | Optional. Another server address (default `https://praesago.com/api/mcp`). |

## Development

```bash
PYTHONPATH=src pytest -q tests                 # unit tests, no network
PRAESAGO_LIVE=1 PYTHONPATH=src pytest -q tests  # also one call to the real server
```

MIT licence.

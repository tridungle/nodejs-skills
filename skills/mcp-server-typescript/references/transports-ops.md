# Transports, auth, testing, deployment

Load when choosing how a server is run and reached, securing it, or testing it.

## Choosing a transport

| | stdio | Streamable HTTP |
|---|---|---|
| Runs as | A child process the client launches | A long-running web service |
| Users | One local user | Many, remote |
| Auth | Inherits the local user; credentials from env | Required: OAuth 2.1 / bearer tokens per the MCP authorization spec |
| Typical use | Developer tools, local files, CLI wrappers | Shared team or SaaS integrations |
| Logging | stderr only | Normal structured logging |

The legacy HTTP+SSE transport is deprecated; build new remote servers on Streamable HTTP. Supporting both stdio and HTTP from one codebase is a small `server.ts` switch on a flag or env var — tools are registered once.

## stdio rules

- stdout is the protocol channel: no `console.log`, no banner, no dependency that prints to stdout. Route logs to stderr.
- Read configuration from environment variables set in the client's server config; validate them at start and exit with a clear stderr message if missing.
- Exit cleanly when stdin closes.

## Streamable HTTP rules

- One endpoint (e.g. `/mcp`) handling POST (and GET for the server-to-client stream if used); mount it in the existing HTTP app if there is one.
- Stateful mode: the SDK issues a session id header; keep a transport per session and clean it up on close/timeout. Stateless mode: a new server/transport per request — simpler to scale horizontally, no server-initiated messages.
- Validate the `Origin` header and bind to `127.0.0.1` when serving locally, to block DNS-rebinding attacks.
- Authenticate every request; map the token to a user and pass that identity to services. Do not forward the client's token to upstream APIs unless it was issued for them.
- Apply body size limits, timeouts and rate limits as for any HTTP API.

## Testing

- **Unit**: services tested as usual, without MCP.
- **Handler level**: connect a client and the server through the SDK's in-memory transport pair; call `listTools`, assert names and schemas; call each tool with valid, invalid and edge inputs; assert `isError` and messages for failure paths.
- **Manual**: the MCP Inspector (`npx @modelcontextprotocol/inspector` pointed at the server command or URL) to browse tools and run calls.
- **Description quality**: give a model the tool list and a handful of invented user requests; check it picks the intended tool. A wrong pick is fixed in the description, not by adding a tool.

## Packaging and deployment

- stdio servers ship as an npm package with a `bin` entry (shebang, compiled JS) so clients can launch it with `npx`; document the env vars it needs.
- Pin the SDK version range; read the SDK changelog before upgrading a major version.
- HTTP servers deploy like any Node service: health endpoint, graceful shutdown, structured logs, secrets from the environment.
- Version the server (`name` + `version` in the server info) and treat tool names and required arguments as a public contract: renaming a tool breaks every saved client config and prompt that references it.

## Checks

- Run the server in stdio mode and confirm the first bytes on stdout are a JSON-RPC message, with logs only on stderr.
- `listTools` returns every tool with a description and an input schema with no unbounded strings.
- Call each tool with a missing required argument: a protocol error, not a crash.
- Call a tool for a non-existent id: an error result with an actionable message.
- HTTP: a request without a token is rejected; a request with a foreign `Origin` is rejected.

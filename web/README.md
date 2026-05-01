# Learn Your Way — Web UI

The React + TypeScript + Vite frontend for Learn Your Way, a self-hosted educational platform that transforms PDFs into personalized, multimodal, assessment-driven study experiences.

## Tech Stack

- **Framework**: React 18 with TypeScript
- **Build tool**: Vite (hot module replacement, fast builds)
- **HTTP Client**: TanStack Query (data fetching and caching)
- **Routing**: TanStack Router
- **Backend**: FastAPI JSON API (usually running on `http://localhost:8000`)
- **Package manager**: pnpm

## Prerequisites

Before setting up the web UI, ensure you have:

- **Node.js** ≥ 20.19 (run `node --version` to check)
- **pnpm** (install with `npm install -g pnpm`)
- Access to the backend API (see [Backend Setup](#backend-setup) below)

Optional:
- **Docker** (for running backend services in containers)
- **uv** (Python package manager; used for the backend)

## Quick Start

### 1. First-Time Setup

Clone the repository and navigate to the web directory:

```bash
git clone https://github.com/andromdaa/learn-your-way.git
cd learn-your-way/web
```

Install dependencies:

```bash
pnpm install
```

### 2. Run the Dev Server

The development server proxies API requests to `http://localhost:8000` and includes hot module replacement (HMR) for instant feedback as you edit code.

```bash
pnpm dev
```

The UI will be available at `http://localhost:5173`. Open it in your browser — changes to React components, styles, and logic auto-refresh in real time.

### 3. Backend Setup

The web UI requires a running backend API. In another terminal, start the FastAPI server:

```bash
# From the project root
uvicorn lyw_core.api.app:app --reload
```

The API will be available at `http://localhost:8000`.

For full functionality, you may also need to run:

- **Arq worker** (processes async ingest jobs):
  ```bash
  arq lyw_core.worker.settings.WorkerSettings
  ```
  (Requires Redis running; see Docker Compose setup below)

- **Full stack with Docker**:
  ```bash
  docker-compose up
  ```
  This starts Ollama (LLM), Redis, Qdrant (vector store), and other services.

If you need just the core API without background jobs:

```bash
uvicorn lyw_core.api.app:app --reload
```

## Development Workflow

### Day-to-Day Development

1. **Start the backend** (once per session):
   ```bash
   uvicorn lyw_core.api.app:app --reload
   ```

2. **Start the Vite dev server** (in the `web/` directory):
   ```bash
   pnpm dev
   ```

3. **Edit components and styles** — changes appear instantly in your browser thanks to HMR.

The Vite dev server proxies requests to `/v1/*`, `/healthz`, and `/openapi.json` to the backend running on port 8000.

### Code Generation from OpenAPI

The web UI generates TypeScript types and API client code from the backend's OpenAPI schema:

```bash
pnpm codegen
```

This reads `/openapi.json` from the running backend (at `http://localhost:8000/openapi.json`) and generates client types. Run this after any backend API changes.

**Note**: The backend must be running for codegen to succeed.

## Quality Gates

Before committing or opening a pull request, run the quality checks:

### Linting & Formatting

```bash
pnpm lint        # ESLint
pnpm format      # Prettier
```

### Type Checking

```bash
pnpm typecheck
```

### Testing

```bash
pnpm test        # Run unit tests
```

### Build Verification

```bash
pnpm build       # Production build (should complete with no errors)
```

### All-in-One Check

```bash
pnpm check
```

This runs lint, format, typecheck, test, and build in sequence. All must pass before your PR is ready.

## Production Build & Preview

### Build for Production

```bash
pnpm build
```

This creates an optimized bundle in the `dist/` directory. The FastAPI server serves this as static files when running in production.

### Preview the Production Build

Test the production bundle locally:

```bash
pnpm preview
```

This starts a local preview server (usually on port `4173`) serving the production-optimized build. Use this to verify:
- Performance characteristics
- Production-like environment behavior
- Missing assets or loading issues

## Configuration

### Vite Configuration

Vite config is in `vite.config.ts`. Key settings:

- **Proxy target**: Backend API URL (default: `http://localhost:8000`)
- **Port**: Development server runs on `5173`; preview on `4173`

### TypeScript Configuration

- `tsconfig.app.json` — TypeScript config for application code
- `tsconfig.node.json` — Config for Vite and build tooling

### Environment Variables

Create a `.env` or `.env.local` file in the `web/` directory for environment-specific settings:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_ENVIRONMENT=development
```

(These must be prefixed with `VITE_` to be exposed to the browser.)

## Troubleshooting

### "Cannot find module" or TypeScript errors

**Solution**: Run `pnpm install` and `pnpm codegen` to regenerate client types from the OpenAPI schema.

### Backend API returns 404 or connection refused

**Problem**: The backend is not running.

**Solution**: In another terminal, start the backend:
```bash
uvicorn lyw_core.api.app:app --reload
```

### Dev server shows blank page or "Cannot GET /"

**Problem**: The UI bundle is not being served.

**Solution**: Check that `pnpm dev` is running and no errors appear in the terminal. If errors occur, review the stack trace — often a broken import or missing dependency.

### "Port 5173 already in use"

**Problem**: Another process is using the port.

**Solution**: Kill the process on port 5173 or specify a different port:
```bash
pnpm dev -- --port 3000
```

### Build fails with "Failed to parse x.ts"

**Problem**: A TypeScript or syntax error in your code.

**Solution**: Check the error message for the file and line number. Fix the syntax and run `pnpm build` again.

### OpenAPI codegen fails

**Problem**: The backend is not running or `/openapi.json` is not accessible.

**Solution**: Ensure the backend is running:
```bash
uvicorn lyw_core.api.app:app --reload
# Verify: curl http://localhost:8000/openapi.json
```

Then retry `pnpm codegen`.

### TypeScript type errors in generated code

**Problem**: The OpenAPI schema changed and generated types are incompatible.

**Solution**: Regenerate types:
```bash
rm src/generated  # Remove cached types
pnpm codegen      # Regenerate from current schema
```

## Project Structure

```
web/
├── src/
│   ├── components/     # Reusable React components
│   ├── hooks/          # Custom React hooks
│   ├── pages/          # Page components (one per route)
│   ├── generated/      # Generated OpenAPI types (from codegen)
│   ├── styles/         # Global and component styles
│   ├── App.tsx         # Main app component with routing
│   └── main.tsx        # Entry point
├── vite.config.ts      # Vite configuration
├── tsconfig.*.json     # TypeScript configuration
├── package.json        # Dependencies and scripts
└── README.md           # This file
```

## Next Steps

- **First PR?** Ensure `pnpm check` passes, including lint, typecheck, test, and build.
- **API changes?** Run `pnpm codegen` to sync TypeScript types.
- **Stuck?** Review the troubleshooting section above or check the backend logs.
- **Questions?** See the main repo's [AGENTS.md](../AGENTS.md) for architecture and development guidelines.

## License

This project is licensed under the same terms as the main Learn Your Way repository.

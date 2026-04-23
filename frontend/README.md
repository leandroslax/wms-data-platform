# WMS Frontend

React + Vite frontend for the local WMS Data Platform.

## Development

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies API calls to `http://localhost:8000`.

## Production Build

```bash
cd frontend
npm run build
```

The build writes static assets to `../app/static`, which FastAPI serves at `/`.

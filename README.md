# Visual Inspector

AI-powered visual quality inspection for manufacturing — UI prototype.

**Current phase: UI and navigation only.** There is no real AI/CV pipeline, backend, or model
training yet. See [`docs/PRODUCT_SCOPE.md`](docs/PRODUCT_SCOPE.md) for the full picture and
[`docs/ROADMAP.md`](docs/ROADMAP.md) for what's next.

## Getting started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The four screens are reachable from the
sidebar, or directly at `/`, `/annotation`, `/analysis`, `/training`.

## Checks

```bash
npm run build   # production build, also runs the TypeScript check
npm run lint     # ESLint
```

## Docs

- [`CLAUDE.md`](CLAUDE.md) — instructions for working in this repo (stack, conventions, hard
  rules around demo data).
- [`docs/PRODUCT_SCOPE.md`](docs/PRODUCT_SCOPE.md) — product vision and current boundaries.
- [`docs/UI_DESIGN_SPEC.md`](docs/UI_DESIGN_SPEC.md) — visual direction, layout, reusable
  patterns.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — stack choices, folder layout, how future
  phases plug in.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — planned implementation phases.

## Stack

Next.js (App Router) + TypeScript + Tailwind CSS v4 + shadcn/ui + lucide-react. No backend yet.

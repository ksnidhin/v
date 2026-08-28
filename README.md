# Premium Vintage Watch E-Commerce Platform

A headless, high-performance e-commerce platform for selling single-unit luxury vintage timepieces.

## Architecture & Monorepo Structure

* `apps/storefront` — Next.js 15+ (App Router) customer storefront
* `apps/admin` — Refine.dev + React + Vite internal operational admin dashboard
* `packages/shared` — Shared TypeScript data SDK (`@watch-platform/shared`)
* `backend` — Dockerized WordPress 6.5 + WooCommerce 9.x (HPOS enabled) + Redis engine

## Quick Start (Backend - Phase 1)

1. Open PowerShell terminal in the `backend` folder:
   ```powershell
   cd c:\Users\PC\.gemini\antigravity\scratch\violet-main\backend
   ```

2. Start Docker containers:
   ```powershell
   docker compose up -d
   ```

3. Run automated provisioner:
   ```bash
   bash scripts/setup-backend.sh
   ```

4. Verify REST API:
   ```powershell
   curl http://localhost:8080/wp-json/wc/v3/products
   ```

// Route registry (U1) — auto-collects feature routes so main.tsx never needs editing by streams.
// Each Phase 1 stream adds a `src/features/<name>/routes.tsx` that default-exports FeatureRoutes.
import type { RouteObject } from "react-router-dom";

export type RouteScope = "customer" | "admin";

export interface FeatureRoutes {
  scope: RouteScope;
  routes: RouteObject[];
}

// Vite import.meta.glob auto-discovers every feature routes module at build time.
export function collectRoutes(): Record<RouteScope, RouteObject[]> {
  const modules = import.meta.glob<{ default: FeatureRoutes }>("../features/**/routes.tsx", {
    eager: true,
  });
  const result: Record<RouteScope, RouteObject[]> = { customer: [], admin: [] };
  for (const mod of Object.values(modules)) {
    const fr = mod.default;
    if (fr && (fr.scope === "customer" || fr.scope === "admin")) {
      result[fr.scope].push(...fr.routes);
    }
  }
  return result;
}

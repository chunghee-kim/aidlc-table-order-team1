// U5/D — monitoring route (/admin/monitoring). Auto-collected by the route registry (main.tsx untouched).
import type { FeatureRoutes } from "../../../app/route-registry";
import { MonitoringDashboardView } from "./MonitoringDashboardView";

const routes: FeatureRoutes = {
  scope: "admin",
  routes: [{ path: "monitoring", element: <MonitoringDashboardView /> }],
};

export default routes;

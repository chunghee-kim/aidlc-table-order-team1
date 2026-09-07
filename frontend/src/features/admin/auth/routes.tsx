// Admin auth routes (U2/A) — collected by the route registry (main.tsx not edited).
import type { FeatureRoutes } from "../../../app/route-registry";
import { AdminLoginView } from "./AdminLoginView";
import { TableSetupView } from "./TableSetupView";

const routes: FeatureRoutes = {
  scope: "admin",
  routes: [
    { path: "login", element: <AdminLoginView /> },
    { path: "table-setup", element: <TableSetupView /> },
  ],
};
export default routes;

// Customer auto-login routes (U2/A) — collected by the route registry (main.tsx not edited).
import type { FeatureRoutes } from "../../../app/route-registry";
import { AutoLoginBootstrap } from "./AutoLoginBootstrap";
import { TableLoginView } from "./TableLoginView";

const routes: FeatureRoutes = {
  scope: "customer",
  routes: [
    { path: "start", element: <AutoLoginBootstrap /> },
    { path: "table-login", element: <TableLoginView /> },
  ],
};
export default routes;

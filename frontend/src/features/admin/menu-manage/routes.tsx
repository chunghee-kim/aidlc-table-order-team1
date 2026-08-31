// Admin menu-manage route (U3/B) — /admin/menu-manage. Auto-collected by the route registry.
import type { FeatureRoutes } from "../../../app/route-registry";
import { MenuManageView } from "./MenuManageView";

const routes: FeatureRoutes = {
  scope: "admin",
  routes: [{ path: "menu-manage", element: <MenuManageView /> }],
};

export default routes;

// Customer menu route (U3/B) — /customer/menu. Auto-collected by the route registry.
import type { FeatureRoutes } from "../../../app/route-registry";
import { MenuBrowseView } from "./MenuBrowseView";

const routes: FeatureRoutes = {
  scope: "customer",
  routes: [{ path: "menu", element: <MenuBrowseView /> }],
};

export default routes;

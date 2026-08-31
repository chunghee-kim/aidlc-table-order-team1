// U6 — 라우트 레지스트리 등록(자동 수집). main.tsx 미편집.
import type { FeatureRoutes } from "../../../app/route-registry";
import { OrderHistoryView } from "./OrderHistoryView";

const routes: FeatureRoutes = {
  scope: "admin",
  routes: [{ path: "history", element: <OrderHistoryView /> }], // /admin/history
};
export default routes;

// U6 — 라우트 레지스트리 등록(자동 수집). main.tsx 미편집.
import type { FeatureRoutes } from "../../../app/route-registry";
import { CloseTableView } from "./CloseTableView";

const routes: FeatureRoutes = {
  scope: "admin",
  routes: [{ path: "table-close", element: <CloseTableView /> }], // /admin/table-close
};
export default routes;

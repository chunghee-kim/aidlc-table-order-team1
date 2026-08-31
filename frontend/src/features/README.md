# features/ — 기능(feature) 기반 폴더 (Phase 1 스트림 소유)

각 Phase 1 스트림은 자기 기능을 이 디렉터리 아래에 둡니다. 라우트는 **라우트 레지스트리** 규약으로 등록하세요(`main.tsx` 편집 금지).

## 라우트 등록 규약
`src/features/<name>/routes.tsx` 파일에서 `FeatureRoutes` 를 **default export** 하면 `main.tsx`가 자동 수집합니다.

```tsx
import type { FeatureRoutes } from "../../app/route-registry";
import { MenuBrowseView } from "./MenuBrowseView";

const routes: FeatureRoutes = {
  scope: "customer", // 또는 "admin"
  routes: [{ path: "menu", element: <MenuBrowseView /> }], // path는 /customer 하위 상대경로
};
export default routes;
```

## 스트림 배정 (parallel-execution.md §4)
- A·U2: `features/admin/login`, `features/admin/table-setup`, `features/customer/auto-login`
- B·U3: `features/customer/menu`, `features/admin/menu-manage`
- C·U4: `features/customer/cart`, `features/customer/orders`
- D·U5: `features/admin/monitoring`
- E·U6: `features/admin/history`, 이용완료 플로우

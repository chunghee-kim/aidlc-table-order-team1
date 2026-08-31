// U4/C — customer cart & order routes (auto-collected by the route registry; main.tsx untouched).
import type { FeatureRoutes } from "../../../app/route-registry";
import CartView from "./CartView";
import CurrentOrdersView from "./CurrentOrdersView";
import OrderConfirmView from "./OrderConfirmView";
import OrderSuccessView from "./OrderSuccessView";

const routes: FeatureRoutes = {
  scope: "customer",
  routes: [
    { path: "cart", element: <CartView /> },
    { path: "order/confirm", element: <OrderConfirmView /> },
    { path: "order/success", element: <OrderSuccessView /> },
    { path: "orders", element: <CurrentOrdersView /> },
  ],
};

export default routes;

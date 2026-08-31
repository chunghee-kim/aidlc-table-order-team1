// App shell + routing (U1) — /customer and /admin route trees. Uses the route registry to collect
// feature routes; streams add features/<name>/routes.tsx and never edit this file.
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Link, Navigate, useRoutes, type RouteObject } from "react-router-dom";

import { AuthProvider } from "./context/auth-context";
import { TableSessionProvider } from "./context/table-session-context";
import { CartProvider } from "./context/cart-context";
import { collectRoutes } from "./app/route-registry";

function CustomerHome() {
  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>고객 화면 (/customer)</h1>
      <p>Phase 0 앱 셸입니다. 메뉴·장바구니·주문 화면은 후속 스트림(U3/U4)이 추가합니다.</p>
      <Link to="/admin">관리자 화면으로</Link>
    </main>
  );
}

function AdminHome() {
  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>관리자 화면 (/admin)</h1>
      <p>Phase 0 앱 셸입니다. 로그인·모니터링·메뉴관리·이력 화면은 후속 스트림(U2/U5/U3/U6)이 추가합니다.</p>
      <Link to="/customer">고객 화면으로</Link>
    </main>
  );
}

function AppRoutes() {
  const { customer, admin } = collectRoutes();
  const routes: RouteObject[] = [
    { path: "/", element: <Navigate to="/customer" replace /> },
    { path: "/customer", children: [{ index: true, element: <CustomerHome /> }, ...customer] },
    { path: "/admin", children: [{ index: true, element: <AdminHome /> }, ...admin] },
    { path: "*", element: <div style={{ padding: 24 }}>404 Not Found</div> },
  ];
  return useRoutes(routes);
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <TableSessionProvider>
          <CartProvider>
            <AppRoutes />
          </CartProvider>
        </TableSessionProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);

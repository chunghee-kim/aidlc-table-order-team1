// App shell + routing (U1) — /customer and /admin route trees. Uses the route registry to collect
// feature routes; features add features/<name>/routes.tsx. The two layouts below give each area a
// persistent top nav so screens flow naturally (customer: auto table session, no login).
import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import {
  BrowserRouter,
  NavLink,
  Navigate,
  Outlet,
  useNavigate,
  useRoutes,
  type RouteObject,
} from "react-router-dom";

import { AuthProvider, useAuth } from "./context/auth-context";
import { TableSessionProvider, saveTableConfig, useTableSession } from "./context/table-session-context";
import { CartProvider, useCart } from "./context/cart-context";
import { collectRoutes } from "./app/route-registry";

// Default demo tablet: a customer opening /customer is auto-provisioned to table 1 (seed password
// = table number) so browsing → cart → order works with no login screen.
const DEFAULT_TABLE = { storeCode: "STORE01", tableNumber: 1, tablePassword: "1" };

const bar: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 4,
  padding: "10px 20px",
  borderBottom: "1px solid #e5e7eb",
  background: "#fff",
  position: "sticky",
  top: 0,
  zIndex: 10,
  fontFamily: "sans-serif",
};

function navLinkStyle({ isActive }: { isActive: boolean }): React.CSSProperties {
  return {
    padding: "8px 14px",
    borderRadius: 8,
    textDecoration: "none",
    fontWeight: 600,
    fontSize: 14,
    color: isActive ? "#fff" : "#374151",
    background: isActive ? "#1f6feb" : "transparent",
  };
}

// --- Customer -------------------------------------------------------------------------------

function CustomerLayout() {
  const { isConfigured, bootstrap, getContext } = useTableSession();
  const cart = useCart();

  useEffect(() => {
    (async () => {
      if (!isConfigured()) saveTableConfig(DEFAULT_TABLE);
      try {
        await bootstrap();
      } catch {
        /* menu still browses; ordering will surface any error */
      }
    })();
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ctx = getContext();
  const count = cart.getItems().reduce((s, i) => s + i.quantity, 0);

  return (
    <div>
      <header style={bar}>
        <strong style={{ fontSize: 16, marginRight: 12 }}>🍽️ 테이블 오더</strong>
        <NavLink to="/customer/menu" style={navLinkStyle}>
          메뉴
        </NavLink>
        <NavLink to="/customer/cart" style={navLinkStyle}>
          장바구니{count > 0 ? ` (${count})` : ""}
        </NavLink>
        <NavLink to="/customer/orders" style={navLinkStyle}>
          주문내역
        </NavLink>
        <span style={{ marginLeft: "auto", color: "#6b7280", fontSize: 13 }}>
          {ctx ? `${ctx.tableId}번 테이블` : "연결 중…"}
        </span>
        <NavLink to="/admin" style={{ ...navLinkStyle({ isActive: false }), color: "#9ca3af", fontWeight: 400 }}>
          관리자
        </NavLink>
      </header>
      <Outlet />
    </div>
  );
}

// --- Admin ----------------------------------------------------------------------------------

function AdminLayout() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const authed = isAuthenticated();

  return (
    <div>
      {authed && (
        <header style={bar}>
          <strong style={{ fontSize: 16, marginRight: 12 }}>🛠️ 관리자</strong>
          <NavLink to="/admin/monitoring" style={navLinkStyle}>
            주문 모니터링
          </NavLink>
          <NavLink to="/admin/menu-manage" style={navLinkStyle}>
            메뉴 관리
          </NavLink>
          <NavLink to="/admin/history" style={navLinkStyle}>
            주문 내역
          </NavLink>
          <NavLink to="/admin/table-close" style={navLinkStyle}>
            테이블 마감
          </NavLink>
          <NavLink to="/admin/table-setup" style={navLinkStyle}>
            테이블 셋업
          </NavLink>
          <button
            onClick={() => {
              logout();
              navigate("/admin/login");
            }}
            style={{ marginLeft: "auto", minHeight: 40, padding: "6px 14px", borderRadius: 8, border: "1px solid #ccc", cursor: "pointer" }}
          >
            로그아웃
          </button>
        </header>
      )}
      <Outlet />
    </div>
  );
}

function AdminIndex() {
  const { isAuthenticated } = useAuth();
  return <Navigate to={isAuthenticated() ? "/admin/monitoring" : "/admin/login"} replace />;
}

function AppRoutes() {
  const { customer, admin } = collectRoutes();
  const routes: RouteObject[] = [
    { path: "/", element: <Navigate to="/customer" replace /> },
    {
      path: "/customer",
      element: <CustomerLayout />,
      children: [{ index: true, element: <Navigate to="/customer/menu" replace /> }, ...customer],
    },
    {
      path: "/admin",
      element: <AdminLayout />,
      children: [{ index: true, element: <AdminIndex /> }, ...admin],
    },
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

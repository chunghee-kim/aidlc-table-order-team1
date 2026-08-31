// MenuBrowseView (U3/B) — customer default screen: category tabs + touch-friendly menu cards.
// Stories: US-C-03 (default screen), US-C-04 (category filter), US-C-05 (details), US-C-06 (44x44px touch).
import { useEffect, useMemo, useState, type CSSProperties } from "react";

import { ApiError } from "../../../shared/api/api-client";
import { Button } from "../../../shared/ui/Button";
import { formatPrice, menuApi, type CategoryView, type MenuView } from "../../menu/menu-api";

export function MenuBrowseView() {
  const [categories, setCategories] = useState<CategoryView[]>([]);
  const [menus, setMenus] = useState<MenuView[]>([]);
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [cats, items] = await Promise.all([menuApi.listCategories(), menuApi.listMenus()]);
        if (cancelled) return;
        setCategories(cats);
        setMenus(items);
        setActiveCategoryId(cats.length > 0 ? cats[0].id : null);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "메뉴를 불러오지 못했습니다.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const visibleMenus = useMemo(
    () => (activeCategoryId == null ? menus : menus.filter((m) => m.category_id === activeCategoryId)),
    [menus, activeCategoryId],
  );

  if (loading) return <main style={page}>메뉴를 불러오는 중…</main>;
  if (error) return <main style={page}>{error}</main>;
  if (categories.length === 0) return <main style={page}>등록된 메뉴가 없습니다.</main>;

  return (
    <main style={page}>
      <h1 style={{ fontSize: 24, margin: "0 0 16px" }}>메뉴</h1>

      <nav style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
        {categories.map((cat) => {
          const active = cat.id === activeCategoryId;
          return (
            <Button
              key={cat.id}
              onClick={() => setActiveCategoryId(cat.id)}
              aria-pressed={active}
              style={{
                background: active ? "#1f6feb" : "#fff",
                color: active ? "#fff" : "#1f2328",
                borderColor: active ? "#1f6feb" : "#ccc",
                fontWeight: active ? 700 : 400,
              }}
            >
              {cat.name}
            </Button>
          );
        })}
      </nav>

      {visibleMenus.length === 0 ? (
        <p>이 카테고리에는 메뉴가 없습니다.</p>
      ) : (
        <ul style={grid}>
          {visibleMenus.map((menu) => (
            <MenuCard key={menu.id} menu={menu} />
          ))}
        </ul>
      )}
    </main>
  );
}

function MenuCard({ menu }: { menu: MenuView }) {
  return (
    <li style={card} aria-disabled={!menu.is_available}>
      <div style={imageWrap}>
        {menu.image_url ? (
          <img
            src={menu.image_url}
            alt={menu.name}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <span style={{ color: "#8b949e" }}>이미지 없음</span>
        )}
        {!menu.is_available && <span style={soldOut}>품절</span>}
      </div>
      <div style={{ padding: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
          <strong style={{ fontSize: 16 }}>{menu.name}</strong>
          <span style={{ fontSize: 16, whiteSpace: "nowrap" }}>{formatPrice(menu.price)}</span>
        </div>
        {menu.description && (
          <p style={{ margin: "8px 0 0", color: "#57606a", fontSize: 14 }}>{menu.description}</p>
        )}
      </div>
    </li>
  );
}

const page: CSSProperties = { padding: 24, fontFamily: "sans-serif", maxWidth: 960, margin: "0 auto" };
const grid: CSSProperties = {
  listStyle: "none",
  padding: 0,
  margin: 0,
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
  gap: 16,
};
const card: CSSProperties = {
  border: "1px solid #d0d7de",
  borderRadius: 12,
  overflow: "hidden",
  background: "#fff",
};
const imageWrap: CSSProperties = {
  position: "relative",
  width: "100%",
  aspectRatio: "3 / 2",
  background: "#f6f8fa",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};
const soldOut: CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "rgba(0,0,0,0.45)",
  color: "#fff",
  fontWeight: 700,
  fontSize: 18,
};

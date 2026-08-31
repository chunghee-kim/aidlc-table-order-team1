// MenuManageView (U3/B) — admin menu CRUD + display ordering.
// Stories: US-A-16 (register), US-A-17 (edit/delete), US-A-18 (reorder).
import { useCallback, useEffect, useMemo, useState, type CSSProperties, type FormEvent } from "react";

import { ApiError } from "../../../shared/api/api-client";
import { Button } from "../../../shared/ui/Button";
import {
  formatPrice,
  menuApi,
  type CategoryView,
  type MenuInput,
  type MenuView,
} from "../../menu/menu-api";

const EMPTY_FORM = { name: "", price: "", description: "", image_url: "" };

export function MenuManageView() {
  const [categories, setCategories] = useState<CategoryView[]>([]);
  const [menus, setMenus] = useState<MenuView[]>([]);
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [cats, items] = await Promise.all([menuApi.listCategories(), menuApi.listMenus()]);
    setCategories(cats);
    setMenus(items);
    setCategoryId((prev) => prev ?? (cats.length > 0 ? cats[0].id : null));
  }, []);

  useEffect(() => {
    load().catch((err) => setError(toMessage(err)));
  }, [load]);

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (categoryId == null) {
      setError("카테고리를 선택하세요.");
      return;
    }
    const price = Number(form.price);
    if (!form.name.trim()) {
      setError("메뉴명은 필수입니다.");
      return;
    }
    if (!Number.isFinite(price) || price <= 0) {
      setError("가격은 0보다 큰 숫자여야 합니다.");
      return;
    }
    const payload: MenuInput = {
      name: form.name.trim(),
      price,
      description: form.description.trim() || null,
      image_url: form.image_url.trim() || null,
      category_id: categoryId,
    };
    setBusy(true);
    try {
      if (editingId == null) await menuApi.create(payload);
      else await menuApi.update(editingId, payload);
      resetForm();
      await load();
    } catch (err) {
      setError(toMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const startEdit = (menu: MenuView) => {
    setEditingId(menu.id);
    setCategoryId(menu.category_id);
    setForm({
      name: menu.name,
      price: String(menu.price),
      description: menu.description ?? "",
      image_url: menu.image_url ?? "",
    });
  };

  const remove = async (menu: MenuView) => {
    if (!window.confirm(`'${menu.name}' 메뉴를 삭제할까요?`)) return;
    setBusy(true);
    try {
      await menuApi.remove(menu.id);
      if (editingId === menu.id) resetForm();
      await load();
    } catch (err) {
      setError(toMessage(err));
    } finally {
      setBusy(false);
    }
  };

  // Move a menu up/down within its category and persist the new order.
  const move = async (menu: MenuView, delta: -1 | 1) => {
    const siblings = menus
      .filter((m) => m.category_id === menu.category_id)
      .sort((a, b) => a.display_order - b.display_order);
    const idx = siblings.findIndex((m) => m.id === menu.id);
    const target = idx + delta;
    if (target < 0 || target >= siblings.length) return;
    const reordered = [...siblings];
    [reordered[idx], reordered[target]] = [reordered[target], reordered[idx]];
    setBusy(true);
    try {
      await menuApi.reorder(menu.category_id, reordered.map((m) => m.id));
      await load();
    } catch (err) {
      setError(toMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const grouped = useMemo(() => {
    return categories.map((cat) => ({
      category: cat,
      items: menus
        .filter((m) => m.category_id === cat.id)
        .sort((a, b) => a.display_order - b.display_order),
    }));
  }, [categories, menus]);

  return (
    <main style={page}>
      <h1 style={{ fontSize: 24, margin: "0 0 16px" }}>메뉴 관리</h1>
      {error && <p style={{ color: "#cf222e" }}>{error}</p>}

      <form onSubmit={submit} style={formBox}>
        <h2 style={{ fontSize: 18, margin: 0 }}>{editingId == null ? "새 메뉴 등록" : "메뉴 수정"}</h2>
        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "1fr 1fr" }}>
          <label style={label}>
            메뉴명 *
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              style={input}
            />
          </label>
          <label style={label}>
            가격(원) *
            <input
              type="number"
              min={1}
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
              style={input}
            />
          </label>
          <label style={label}>
            카테고리 *
            <select
              value={categoryId ?? ""}
              onChange={(e) => setCategoryId(Number(e.target.value))}
              style={input}
            >
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </label>
          <label style={label}>
            이미지 URL
            <input
              value={form.image_url}
              onChange={(e) => setForm({ ...form, image_url: e.target.value })}
              style={input}
            />
          </label>
        </div>
        <label style={label}>
          설명
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            style={{ ...input, minHeight: 60 }}
          />
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          <Button type="submit" disabled={busy} style={{ background: "#1f6feb", color: "#fff", borderColor: "#1f6feb" }}>
            {editingId == null ? "등록" : "저장"}
          </Button>
          {editingId != null && (
            <Button type="button" onClick={resetForm} disabled={busy}>
              취소
            </Button>
          )}
        </div>
      </form>

      {grouped.map(({ category, items }) => (
        <section key={category.id} style={{ marginTop: 24 }}>
          <h2 style={{ fontSize: 18, borderBottom: "1px solid #d0d7de", paddingBottom: 4 }}>{category.name}</h2>
          {items.length === 0 ? (
            <p style={{ color: "#57606a" }}>메뉴 없음</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {items.map((menu, idx) => (
                <li key={menu.id} style={row}>
                  <span style={{ flex: 1 }}>
                    <strong>{menu.name}</strong> — {formatPrice(menu.price)}
                    {!menu.is_available && <em style={{ color: "#cf222e" }}> (품절)</em>}
                  </span>
                  <Button type="button" onClick={() => move(menu, -1)} disabled={busy || idx === 0} aria-label="위로">
                    ↑
                  </Button>
                  <Button
                    type="button"
                    onClick={() => move(menu, 1)}
                    disabled={busy || idx === items.length - 1}
                    aria-label="아래로"
                  >
                    ↓
                  </Button>
                  <Button type="button" onClick={() => startEdit(menu)} disabled={busy}>
                    수정
                  </Button>
                  <Button
                    type="button"
                    onClick={() => remove(menu)}
                    disabled={busy}
                    style={{ color: "#cf222e", borderColor: "#cf222e" }}
                  >
                    삭제
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </main>
  );
}

function toMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "요청을 처리하지 못했습니다.";
}

const page: CSSProperties = { padding: 24, fontFamily: "sans-serif", maxWidth: 900, margin: "0 auto" };
const formBox: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 12,
  border: "1px solid #d0d7de",
  borderRadius: 12,
  padding: 16,
  background: "#fff",
};
const label: CSSProperties = { display: "flex", flexDirection: "column", gap: 4, fontSize: 14 };
const input: CSSProperties = { padding: 8, borderRadius: 8, border: "1px solid #ccc", fontSize: 14, minHeight: 40 };
const row: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  padding: "8px 0",
  borderBottom: "1px solid #eaeef2",
};

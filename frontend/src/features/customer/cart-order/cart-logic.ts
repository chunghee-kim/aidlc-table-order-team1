// U4/C — pure cart operations (no React/DOM). Reused by CartContext and tested by fast-check.
// 🔬 Invariants: total = Σ(unitPrice × quantity); quantity >= 1; localStorage round-trip.
import type { CartItem, CartMenu } from "../../../context/cart-context";

export const CART_STORAGE_KEY = "cart:v1";

/** Add a menu: absent -> quantity 1, already present -> quantity + 1. Returns a new array. */
export function addItem(items: CartItem[], menu: CartMenu): CartItem[] {
  const existing = items.find((i) => i.menuId === menu.id);
  if (existing) {
    return items.map((i) => (i.menuId === menu.id ? { ...i, quantity: i.quantity + 1 } : i));
  }
  return [...items, { menuId: menu.id, name: menu.name, unitPrice: menu.price, quantity: 1 }];
}

/** Set an item's quantity. quantity <= 0 removes it (no zero/negative lines, US-C-08). */
export function setQuantity(items: CartItem[], menuId: number, qty: number): CartItem[] {
  if (qty <= 0) return removeItem(items, menuId);
  return items.map((i) => (i.menuId === menuId ? { ...i, quantity: qty } : i));
}

export function removeItem(items: CartItem[], menuId: number): CartItem[] {
  return items.filter((i) => i.menuId !== menuId);
}

export function total(items: CartItem[]): number {
  return items.reduce((sum, i) => sum + i.unitPrice * i.quantity, 0);
}

/** Serialize for localStorage persistence (US-C-11). */
export function serialize(items: CartItem[]): string {
  return JSON.stringify(items);
}

/** Restore from localStorage. Invalid/absent payloads yield an empty cart (never throws). */
export function deserialize(raw: string | null): CartItem[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (i) =>
          i &&
          typeof i.menuId === "number" &&
          typeof i.name === "string" &&
          typeof i.unitPrice === "number" &&
          typeof i.quantity === "number" &&
          i.quantity >= 1,
      )
      .map((i) => ({ menuId: i.menuId, name: i.name, unitPrice: i.unitPrice, quantity: i.quantity }));
  } catch {
    return [];
  }
}

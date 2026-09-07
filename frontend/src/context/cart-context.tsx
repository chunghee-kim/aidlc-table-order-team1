// CartContext (contract frozen in Phase 0; implemented by U4/C). component-methods.md §4.3
// 🔬 Invariants (U4 PBT): getTotal = Σ(unit_price × quantity), quantity >= 1,
// localStorage round-trip (save -> restore == original). Pure ops live in
// features/customer/cart-order/cart-logic.ts (tested by fast-check).
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import * as cart from "../features/customer/cart-order/cart-logic";

export interface CartMenu {
  id: number;
  name: string;
  price: number;
}

export interface CartItem {
  menuId: number;
  name: string;
  unitPrice: number;
  quantity: number;
}

export interface CartContextValue {
  addItem(menu: CartMenu): void; // absent -> qty 1, present -> +1
  setQuantity(menuId: number, qty: number): void; // qty <= 0 removes
  removeItem(menuId: number): void;
  clear(): void;
  getTotal(): number;
  getItems(): CartItem[];
}

const CartContext = createContext<CartContextValue | null>(null);

function readInitial(): CartItem[] {
  if (typeof window === "undefined") return [];
  return cart.deserialize(window.localStorage.getItem(cart.CART_STORAGE_KEY));
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(readInitial);

  // Persist on every change so a refresh restores the cart (US-C-11).
  useEffect(() => {
    window.localStorage.setItem(cart.CART_STORAGE_KEY, cart.serialize(items));
  }, [items]);

  const value = useMemo<CartContextValue>(
    () => ({
      addItem: (menu) => setItems((prev) => cart.addItem(prev, menu)),
      setQuantity: (menuId, qty) => setItems((prev) => cart.setQuantity(prev, menuId, qty)),
      removeItem: (menuId) => setItems((prev) => cart.removeItem(prev, menuId)),
      clear: () => setItems([]),
      getTotal: () => cart.total(items),
      getItems: () => items,
    }),
    [items],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}

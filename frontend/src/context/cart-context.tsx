// CartContext (contract frozen in Phase 0; implemented by U4/C). component-methods.md §4.3
// 🔬 Invariants (U4 PBT): getTotal = Σ(unit_price × quantity), quantity >= 1,
// localStorage round-trip (save -> restore == original).
import { createContext, useContext, type ReactNode } from "react";

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

// Phase 0 stub. U4/C provides the real localStorage-backed implementation.
const stubValue: CartContextValue = {
  addItem(_menu) {
    throw new Error("CartContext.addItem not implemented (U4/C owns).");
  },
  setQuantity(_menuId, _qty) {
    throw new Error("CartContext.setQuantity not implemented (U4/C owns).");
  },
  removeItem(_menuId) {
    throw new Error("CartContext.removeItem not implemented (U4/C owns).");
  },
  clear() {
    throw new Error("CartContext.clear not implemented (U4/C owns).");
  },
  getTotal() {
    return 0;
  },
  getItems() {
    return [];
  },
};

export function CartProvider({ children }: { children: ReactNode }) {
  return <CartContext.Provider value={stubValue}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}

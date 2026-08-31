// U4/C property-based tests (fast-check) — cart invariants (US-C-08/11/12).
// 🔬 total = Σ(unitPrice × quantity); quantity >= 1; localStorage round-trip (save -> restore).
import fc from "fast-check";
import { describe, expect, it } from "vitest";

import type { CartItem, CartMenu } from "../../../context/cart-context";
import {
  addItem,
  deserialize,
  MAX_QUANTITY,
  removeItem,
  serialize,
  setQuantity,
  total,
} from "./cart-logic";

const menuArb: fc.Arbitrary<CartMenu> = fc.record({
  id: fc.integer({ min: 1, max: 50 }),
  name: fc.string({ minLength: 1, maxLength: 20 }),
  price: fc.integer({ min: 1, max: 1_000_000 }),
});

const itemArb: fc.Arbitrary<CartItem> = fc.record({
  menuId: fc.integer({ min: 1, max: 50 }),
  name: fc.string({ minLength: 1, maxLength: 20 }),
  unitPrice: fc.integer({ min: 1, max: 1_000_000 }),
  quantity: fc.integer({ min: 1, max: 999 }),
});

// De-duplicate by menuId so a cart never has two lines for the same menu.
const cartArb: fc.Arbitrary<CartItem[]> = fc
  .array(itemArb, { maxLength: 20 })
  .map((items) => [...new Map(items.map((i) => [i.menuId, i])).values()]);

describe("cart totals", () => {
  it("total = Σ(unitPrice × quantity)", () => {
    fc.assert(
      fc.property(cartArb, (items) => {
        const expected = items.reduce((s, i) => s + i.unitPrice * i.quantity, 0);
        expect(total(items)).toBe(expected);
      }),
    );
  });

  it("adding an existing menu increments quantity, not lines", () => {
    fc.assert(
      fc.property(menuArb, fc.integer({ min: 1, max: 10 }), (menu, times) => {
        let items: CartItem[] = [];
        for (let i = 0; i < times; i++) items = addItem(items, menu);
        expect(items).toHaveLength(1);
        expect(items[0].quantity).toBe(times);
        expect(total(items)).toBe(menu.price * times);
      }),
    );
  });
});

describe("quantity rules", () => {
  it("setQuantity <= 0 removes the item (no zero/negative lines)", () => {
    fc.assert(
      fc.property(cartArb, fc.integer({ max: 0 }), (items, qty) => {
        if (items.length === 0) return;
        const id = items[0].menuId;
        const next = setQuantity(items, id, qty);
        expect(next.find((i) => i.menuId === id)).toBeUndefined();
      }),
    );
  });

  it("every line always has quantity >= 1", () => {
    fc.assert(
      fc.property(cartArb, (items) => {
        expect(items.every((i) => i.quantity >= 1)).toBe(true);
      }),
    );
  });

  it("setQuantity clamps to MAX_QUANTITY (NFR-4)", () => {
    fc.assert(
      fc.property(menuArb, fc.integer({ min: MAX_QUANTITY + 1, max: 100_000 }), (menu, qty) => {
        const items = setQuantity([{ menuId: menu.id, name: menu.name, unitPrice: menu.price, quantity: 1 }], menu.id, qty);
        expect(items[0].quantity).toBe(MAX_QUANTITY);
      }),
    );
  });

  it("addItem never exceeds MAX_QUANTITY (NFR-4)", () => {
    fc.assert(
      fc.property(menuArb, fc.integer({ min: 1, max: 300 }), (menu, times) => {
        let items: CartItem[] = [];
        for (let i = 0; i < times; i++) items = addItem(items, menu);
        expect(items[0].quantity).toBe(Math.min(times, MAX_QUANTITY));
      }),
    );
  });
});

describe("localStorage round-trip (US-C-11)", () => {
  it("deserialize(serialize(items)) === items", () => {
    fc.assert(
      fc.property(cartArb, (items) => {
        expect(deserialize(serialize(items))).toEqual(items);
      }),
    );
  });

  it("deserialize tolerates garbage without throwing", () => {
    expect(deserialize(null)).toEqual([]);
    expect(deserialize("not json")).toEqual([]);
    expect(deserialize("{}")).toEqual([]);
    expect(deserialize('[{"bad":1}]')).toEqual([]);
  });
});

describe("removeItem", () => {
  it("removes exactly the targeted menu", () => {
    fc.assert(
      fc.property(cartArb, (items) => {
        if (items.length === 0) return;
        const id = items[0].menuId;
        const next = removeItem(items, id);
        expect(next.find((i) => i.menuId === id)).toBeUndefined();
        expect(next).toHaveLength(items.length - 1);
      }),
    );
  });
});

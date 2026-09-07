// U6 PBT (fast-check) — buildHistoryQuery: 설정된 필터만 포함 + 라운드트립 무손실.
import fc from "fast-check";
import { describe, expect, it } from "vitest";

import { buildHistoryQuery } from "./query";

const dateArb = fc
  .tuple(
    fc.integer({ min: 2000, max: 2099 }),
    fc.integer({ min: 1, max: 12 }),
    fc.integer({ min: 1, max: 28 }),
  )
  .map(([y, m, d]) => `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`);

describe("buildHistoryQuery (PBT)", () => {
  it("설정된 파라미터만 포함하고 값이 라운드트립된다", () => {
    fc.assert(
      fc.property(
        fc.option(fc.integer({ min: 1, max: 999 }), { nil: null }),
        fc.option(dateArb, { nil: null }),
        fc.option(dateArb, { nil: null }),
        (table, dateFrom, dateTo) => {
          const qs = buildHistoryQuery({ table, dateFrom, dateTo });
          const params = new URLSearchParams(qs.startsWith("?") ? qs.slice(1) : qs);
          expect(params.get("table")).toBe(table == null ? null : String(table));
          expect(params.get("date_from")).toBe(dateFrom ?? null);
          expect(params.get("date_to")).toBe(dateTo ?? null);
        },
      ),
    );
  });

  it("필터가 하나도 없으면 빈 문자열", () => {
    expect(buildHistoryQuery({})).toBe("");
    expect(buildHistoryQuery({ table: null, dateFrom: null, dateTo: null })).toBe("");
    expect(buildHistoryQuery({ dateFrom: "", dateTo: "" })).toBe("");
  });
});

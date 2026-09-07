// U5/D — TableFilterBar (US-A-08). Client-side filter only (Q6): no re-subscribe/re-fetch.
import { Button } from "../../../shared/ui/Button";

export function TableFilterBar({
  tables,
  active,
  onSelect,
}: {
  tables: number[];
  active: number | null;
  onSelect: (n: number | null) => void;
}) {
  const chip = (selected: boolean) => ({
    background: selected ? "#1d4ed8" : "#fff",
    color: selected ? "#fff" : "#333",
    borderColor: selected ? "#1d4ed8" : "#ccc",
  });
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", margin: "12px 0" }}>
      <span style={{ color: "#666", fontSize: 13 }}>테이블 필터:</span>
      <Button style={chip(active === null)} onClick={() => onSelect(null)}>
        전체
      </Button>
      {tables.map((t) => (
        <Button key={t} style={chip(active === t)} onClick={() => onSelect(t)}>
          {t}번
        </Button>
      ))}
    </div>
  );
}

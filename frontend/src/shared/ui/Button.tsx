// Shared touch-friendly button primitive (U1). Min 44x44px (NFR-4).
import type { ButtonHTMLAttributes } from "react";

export function Button(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  const { style, ...rest } = props;
  return (
    <button
      {...rest}
      style={{
        minWidth: 44,
        minHeight: 44,
        padding: "8px 16px",
        borderRadius: 8,
        border: "1px solid #ccc",
        cursor: "pointer",
        ...style,
      }}
    />
  );
}

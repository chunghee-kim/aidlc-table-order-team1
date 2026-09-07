// U5/D — SSE subscription hook wrapping the shared SseClient. Manages connect/disconnect
// lifecycle + exposes connection state; forwards each frame to the dashboard reducer.
import { useEffect, useRef, useState } from "react";

import { useAuth } from "../../../context/auth-context";
import { sseClient, type SseConnState, type SseEvent } from "../../../shared/api/sse-client";

export function useOrderStream(onEvent: (event: SseEvent) => void): { connState: SseConnState } {
  const { getToken } = useAuth();
  const [connState, setConnState] = useState<SseConnState>("connecting");

  // Keep the latest handler without re-subscribing on every render.
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setConnState("reconnecting");
      return;
    }
    const url = `/api/admin/orders/stream?token=${encodeURIComponent(token)}`;
    sseClient.connect(url, (e) => handlerRef.current(e), setConnState);
    return () => sseClient.disconnect();
  }, [getToken]);

  return { connState };
}

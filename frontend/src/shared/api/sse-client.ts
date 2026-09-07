// SseClient (contract frozen in Phase 0; implemented by U5/D). See component-methods.md §4.5.
// connect: EventSource subscription with auto-reconnect (exponential backoff + jitter, cap ~10s).
// On (re)connect the server pushes a snapshot frame that recovers any missed events (US-A-06,
// BR-U5-14/15). The connect/disconnect surface is frozen; `onState` was added by U5/D (owner) as an
// optional, backward-compatible callback for the connection indicator (frontend-components §4).

export type SseConnState = "connecting" | "open" | "reconnecting";

export interface SseEvent {
  // "snapshot" added by U5/D — the reconnect-recovery frame (payload carries the full order list).
  type: "snapshot" | "order_created" | "order_updated" | "order_deleted";
  payload: unknown;
}

export interface SseClient {
  connect(url: string, onEvent: (event: SseEvent) => void, onState?: (state: SseConnState) => void): void;
  disconnect(): void;
}

const BACKOFF_BASE_MS = 1000;
const BACKOFF_CAP_MS = 10_000;

function backoffDelay(attempt: number): number {
  const base = Math.min(BACKOFF_CAP_MS, BACKOFF_BASE_MS * 2 ** attempt);
  return base / 2 + Math.random() * (base / 2); // full-ish jitter
}

class EventSourceSseClient implements SseClient {
  private es: EventSource | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private attempt = 0;
  private closed = false;
  private url = "";
  private onEvent: (event: SseEvent) => void = () => {};
  private onState: (state: SseConnState) => void = () => {};

  connect(url: string, onEvent: (event: SseEvent) => void, onState?: (state: SseConnState) => void): void {
    this.disconnect(); // replace any existing subscription
    this.closed = false;
    this.url = url;
    this.onEvent = onEvent;
    this.onState = onState ?? (() => {});
    this.attempt = 0;
    this.open();
  }

  private open(): void {
    this.onState(this.attempt === 0 ? "connecting" : "reconnecting");
    const es = new EventSource(this.url);
    this.es = es;

    es.onopen = () => {
      this.attempt = 0;
      this.onState("open");
    };

    es.onmessage = (ev: MessageEvent<string>) => {
      let frame: { type?: string };
      try {
        frame = JSON.parse(ev.data);
      } catch {
        return; // ignore malformed frame
      }
      if (!frame || typeof frame.type !== "string") return;
      // Whole frame is handed through as `payload`; the monitoring reducer narrows by `type`.
      this.onEvent({ type: frame.type as SseEvent["type"], payload: frame });
    };

    es.onerror = () => {
      // EventSource would auto-retry, but we drive reconnection ourselves to apply a capped
      // backoff with jitter (BR-U5-15). Close, then schedule a fresh connection.
      es.close();
      this.es = null;
      if (this.closed) return;
      this.onState("reconnecting");
      const delay = backoffDelay(this.attempt);
      this.attempt += 1;
      this.timer = setTimeout(() => this.open(), delay);
    };
  }

  disconnect(): void {
    this.closed = true;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.es) {
      this.es.close();
      this.es = null;
    }
  }
}

export const sseClient: SseClient = new EventSourceSseClient();

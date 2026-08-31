// SseClient (contract frozen in Phase 0; implemented by U5/D). See component-methods.md §4.5.
// connect: EventSource subscription with auto-reconnect (backoff); on reconnect, snapshot recovers
// missed events (US-A-06). Do not change this interface without owner+consumer agreement.

export interface SseEvent {
  type: "order_created" | "order_updated" | "order_deleted";
  payload: unknown;
}

export interface SseClient {
  connect(url: string, onEvent: (event: SseEvent) => void): void;
  disconnect(): void;
}

// Phase 0 stub. U5/D provides the real EventSource + reconnect implementation.
export const sseClient: SseClient = {
  connect() {
    throw new Error("SseClient.connect not implemented (U5/D owns).");
  },
  disconnect() {
    /* no-op until implemented */
  },
};

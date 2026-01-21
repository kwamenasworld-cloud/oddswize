type StreamSubscription = {
  leagues: Set<string> | null;
};

type StreamPayload = {
  type?: string;
  data?: {
    league_keys?: string[];
  };
};

const parseCsvParam = (value: string | null): string[] => {
  if (!value) return [];
  return value
    .split(',')
    .map(part => part.trim().toLowerCase())
    .filter(Boolean);
};

const normalizeLeagueKeys = (value: unknown): string[] => {
  if (!Array.isArray(value)) return [];
  return value
    .map(key => (key || '').toString().trim().toLowerCase())
    .filter(Boolean);
};

const shouldSendToSocket = (subscription: StreamSubscription, payload: StreamPayload): boolean => {
  if (!subscription.leagues || subscription.leagues.size === 0) return true;
  const payloadKeys = normalizeLeagueKeys(payload?.data?.league_keys);
  if (payloadKeys.length === 0) return true;
  return payloadKeys.some(key => subscription.leagues?.has(key));
};

export class OddsStream {
  state: DurableObjectState;
  sockets: Map<WebSocket, StreamSubscription>;

  constructor(state: DurableObjectState) {
    this.state = state;
    this.sockets = new Map();

    for (const socket of this.state.getWebSockets()) {
      const stored = socket.deserializeAttachment() as { league_keys?: string[] } | undefined;
      const leagueKeys = stored?.league_keys ? new Set(stored.league_keys) : null;
      this.sockets.set(socket, { leagues: leagueKeys });
    }
  }

  async fetch(request: Request): Promise<Response> {
    if (request.headers.get('Upgrade') === 'websocket') {
      const url = new URL(request.url);
      const leagueKeys = parseCsvParam(url.searchParams.get('league_keys') || url.searchParams.get('leagues'));
      const pair = new WebSocketPair();
      const client = pair[0];
      const server = pair[1];
      server.accept();

      const subscription = { leagues: leagueKeys.length ? new Set(leagueKeys) : null };
      server.serializeAttachment({ league_keys: leagueKeys });
      this.sockets.set(server, subscription);

      server.addEventListener('message', (event) => {
        try {
          const payload = JSON.parse(event.data as string) as { type?: string; data?: { league_keys?: string[] } };
          if (payload?.type === 'subscribe') {
            const nextKeys = normalizeLeagueKeys(payload.data?.league_keys);
            subscription.leagues = nextKeys.length ? new Set(nextKeys) : null;
            server.serializeAttachment({ league_keys: nextKeys });
          }
        } catch {
          // Ignore malformed messages
        }
      });

      const cleanup = () => {
        this.sockets.delete(server);
      };
      server.addEventListener('close', cleanup);
      server.addEventListener('error', cleanup);

      server.send(JSON.stringify({ type: 'welcome', data: { connected: true, timestamp: new Date().toISOString() } }));
      return new Response(null, { status: 101, webSocket: client });
    }

    if (request.method === 'POST') {
      const payload = await request.json() as StreamPayload;
      const message = JSON.stringify(payload);
      let delivered = 0;

      for (const [socket, subscription] of this.sockets) {
        if (!shouldSendToSocket(subscription, payload)) {
          continue;
        }
        try {
          socket.send(message);
          delivered += 1;
        } catch {
          this.sockets.delete(socket);
        }
      }

      return new Response(JSON.stringify({ success: true, delivered }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response('Not found', { status: 404 });
  }
}

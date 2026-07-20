"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { createClient } from "@/lib/supabase/client";


const EMPTY_EVENTS: RoundtableEvent[] = [];


export interface RoundtableEvent {
  id?: string | null;
  job_id: string;
  event_seq: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

interface EventPage {
  events: RoundtableEvent[];
  last_event_seq: number;
  has_more: boolean;
}

export type RealtimeConnectionState =
  | "idle"
  | "connecting"
  | "subscribed"
  | "reconnecting"
  | "error";

export interface UseRoundtableEventsOptions {
  enabled?: boolean;
  initialEvents?: RoundtableEvent[];
  initialLastEventSeq?: number;
  apiBaseUrl?: string;
  accessToken?: string;
  /** Defaults to the TECH 5.1 topic; override with `roundtable:${jobId}` for Gate 0. */
  channelName?: string;
  fetcher?: typeof fetch;
}

export interface UseRoundtableEventsResult {
  events: RoundtableEvent[];
  lastEventSeq: number;
  connectionState: RealtimeConnectionState;
  error: Error | null;
  reconnect: () => void;
}

export interface EventMergeResult {
  events: RoundtableEvent[];
  pending: RoundtableEvent[];
  lastEventSeq: number;
  hasGap: boolean;
}

export function mergeRoundtableEvents(
  applied: RoundtableEvent[],
  pending: RoundtableEvent[],
  incoming: RoundtableEvent[],
  lastEventSeq: number,
): EventMergeResult {
  const buffered = new Map<number, RoundtableEvent>();
  for (const event of [...pending, ...incoming]) {
    if (isRoundtableEvent(event) && event.event_seq > lastEventSeq) {
      buffered.set(event.event_seq, event);
    }
  }

  const appended: RoundtableEvent[] = [];
  let cursor = lastEventSeq;
  while (buffered.has(cursor + 1)) {
    const event = buffered.get(cursor + 1);
    if (!event) break;
    buffered.delete(cursor + 1);
    appended.push(event);
    cursor += 1;
  }
  const remaining = [...buffered.values()].sort((left, right) => left.event_seq - right.event_seq);
  return {
    events: [...applied, ...appended],
    pending: remaining,
    lastEventSeq: cursor,
    hasGap: remaining.some((event) => event.event_seq > cursor + 1),
  };
}

export function useRoundtableEvents(
  jobId: string,
  options: UseRoundtableEventsOptions = {},
): UseRoundtableEventsResult {
  const {
    enabled = true,
    apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "",
    accessToken,
    channelName = `roundtable:${jobId}:events`,
    fetcher = fetch,
  } = options;
  const initialEvents = options.initialEvents ?? EMPTY_EVENTS;
  const initialState = useMemo(
    () => normalizeInitialEvents(jobId, initialEvents, options.initialLastEventSeq),
    [initialEvents, jobId, options.initialLastEventSeq],
  );
  const [events, setEvents] = useState<RoundtableEvent[]>(initialState.events);
  const [lastEventSeq, setLastEventSeq] = useState(initialState.lastEventSeq);
  const [connectionState, setConnectionState] = useState<RealtimeConnectionState>("idle");
  const [error, setError] = useState<Error | null>(null);
  const [generation, setGeneration] = useState(0);
  const eventsRef = useRef(initialState.events);
  const pendingRef = useRef<RoundtableEvent[]>(initialState.pending);
  const lastEventSeqRef = useRef(initialState.lastEventSeq);

  useEffect(() => {
    eventsRef.current = initialState.events;
    pendingRef.current = initialState.pending;
    lastEventSeqRef.current = initialState.lastEventSeq;
    setEvents(initialState.events);
    setLastEventSeq(initialState.lastEventSeq);
  }, [initialState, jobId]);

  useEffect(() => {
    if (!enabled || !jobId) {
      setConnectionState("idle");
      return;
    }

    const supabase = createClient();
    const controller = new AbortController();
    let active = true;
    let subscribed = false;
    let backfillRunning = false;
    let backfillRequested = false;
    let stagnantGapRetries = 0;

    const apply = (incoming: RoundtableEvent[]) => {
      const merged = mergeRoundtableEvents(
        eventsRef.current,
        pendingRef.current,
        incoming,
        lastEventSeqRef.current,
      );
      eventsRef.current = merged.events;
      pendingRef.current = merged.pending;
      lastEventSeqRef.current = merged.lastEventSeq;
      setEvents(merged.events);
      setLastEventSeq(merged.lastEventSeq);
      return merged;
    };

    const readAccessToken = async () => {
      if (accessToken) return accessToken;
      const { data } = await supabase.auth.getSession();
      return data.session?.access_token;
    };

    const fetchPage = async (): Promise<EventPage> => {
      const token = await readAccessToken();
      const url = new URL(
        `${apiBaseUrl}/v1/roundtables/${encodeURIComponent(jobId)}/events`,
        window.location.origin,
      );
      url.searchParams.set("after_seq", String(lastEventSeqRef.current));
      url.searchParams.set("limit", "200");
      const response = await fetcher(url, {
        cache: "no-store",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`roundtable_event_backfill_${response.status}`);
      const value: unknown = await response.json();
      if (!isEventPage(value)) throw new Error("invalid_roundtable_event_page");
      return value;
    };

    const backfill = async () => {
      if (!subscribed || !active) return;
      if (backfillRunning) {
        backfillRequested = true;
        return;
      }
      backfillRunning = true;
      try {
        do {
          backfillRequested = false;
          const before = lastEventSeqRef.current;
          const page = await fetchPage();
          const merged = apply(page.events);
          if (page.has_more) backfillRequested = true;
          if (merged.hasGap) backfillRequested = true;
          if (merged.lastEventSeq === before && (merged.hasGap || page.has_more)) {
            stagnantGapRetries += 1;
            if (stagnantGapRetries > 2) {
              throw new Error("roundtable_event_sequence_gap");
            }
          } else {
            stagnantGapRetries = 0;
          }
        } while (active && backfillRequested);
        if (active) setError(null);
      } catch (reason) {
        if (active && !controller.signal.aborted) {
          setError(toError(reason));
          setConnectionState("error");
        }
      } finally {
        backfillRunning = false;
      }
    };

    const requestBackfill = (hint?: number) => {
      if (hint !== undefined && hint <= lastEventSeqRef.current) return;
      void backfill();
    };

    setConnectionState("connecting");
    setError(null);
    let channel: ReturnType<typeof supabase.channel> | null = null;
    const connect = async () => {
      try {
        const token = await readAccessToken();
        await supabase.realtime.setAuth(token);
        if (!active) return;
        channel = supabase
          .channel(channelName, { config: { private: true } })
          .on("broadcast", { event: "INSERT" }, ({ payload }) => {
            requestBackfill(extractEventSequence(payload));
          })
          .subscribe((subscriptionStatus) => {
            if (!active) return;
            if (subscriptionStatus === "SUBSCRIBED") {
              subscribed = true;
              setConnectionState("subscribed");
              // The initial backfill starts only after the private subscription is live.
              requestBackfill();
              return;
            }
            if (
              subscriptionStatus === "CHANNEL_ERROR" ||
              subscriptionStatus === "TIMED_OUT" ||
              subscriptionStatus === "CLOSED"
            ) {
              subscribed = false;
              setConnectionState("reconnecting");
            }
          });
      } catch (reason) {
        if (active) {
          setError(toError(reason));
          setConnectionState("error");
        }
      }
    };
    void connect();

    return () => {
      active = false;
      subscribed = false;
      controller.abort();
      if (channel) void supabase.removeChannel(channel);
    };
  }, [accessToken, apiBaseUrl, channelName, enabled, fetcher, generation, jobId]);

  return {
    events,
    lastEventSeq,
    connectionState,
    error,
    reconnect: () => setGeneration((value) => value + 1),
  };
}

function normalizeInitialEvents(
  jobId: string,
  initialEvents: RoundtableEvent[],
  explicitLastEventSeq: number | undefined,
): EventMergeResult {
  const bySequence = new Map<number, RoundtableEvent>();
  for (const event of initialEvents) {
    if (isRoundtableEvent(event) && event.job_id === jobId) {
      bySequence.set(event.event_seq, event);
    }
  }
  const valid = [...bySequence.values()].sort(
    (left, right) => left.event_seq - right.event_seq,
  );
  if (explicitLastEventSeq === undefined) {
    return mergeRoundtableEvents([], [], valid, 0);
  }
  if (!Number.isSafeInteger(explicitLastEventSeq) || explicitLastEventSeq < 0) {
    throw new Error("initialLastEventSeq must be a non-negative safe integer");
  }
  const applied = valid.filter((event) => event.event_seq <= explicitLastEventSeq);
  const pending = valid.filter((event) => event.event_seq > explicitLastEventSeq);
  return mergeRoundtableEvents(applied, pending, [], explicitLastEventSeq);
}

function isRoundtableEvent(value: unknown): value is RoundtableEvent {
  if (typeof value !== "object" || value === null) return false;
  const event = value as Partial<RoundtableEvent>;
  return (
    typeof event.job_id === "string" &&
    Number.isSafeInteger(event.event_seq) &&
    Number(event.event_seq) > 0 &&
    typeof event.event_type === "string" &&
    typeof event.payload === "object" &&
    event.payload !== null &&
    typeof event.created_at === "string"
  );
}

function isEventPage(value: unknown): value is EventPage {
  if (typeof value !== "object" || value === null) return false;
  const page = value as Partial<EventPage>;
  return (
    Array.isArray(page.events) &&
    page.events.every(isRoundtableEvent) &&
    Number.isSafeInteger(page.last_event_seq) &&
    typeof page.has_more === "boolean"
  );
}

function extractEventSequence(value: unknown): number | undefined {
  if (typeof value !== "object" || value === null) return undefined;
  const record = value as Record<string, unknown>;
  const direct = record.event_seq;
  if (typeof direct === "number" && Number.isSafeInteger(direct)) return direct;
  for (const key of ["record", "new", "payload"]) {
    const nested = extractEventSequence(record[key]);
    if (nested !== undefined) return nested;
  }
  return undefined;
}

function toError(value: unknown): Error {
  return value instanceof Error ? value : new Error("roundtable_realtime_failed");
}

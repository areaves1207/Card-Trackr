import { useEffect, useRef, useState } from "react";
import { scan, ScanSession } from "@/lib/api";

/**
 * Polls GET /api/scan/{sessionId} every 2 seconds until status is complete or failed.
 * This is the "long polling" pattern described in ARCHITECTURE.md.
 */
export function useScanSession(sessionId: number | null) {
  const [session, setSession] = useState<ScanSession | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const poll = async () => {
      try {
        const data = await scan.getSession(sessionId);
        setSession(data);
        if (data.status === "complete" || data.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch {
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [sessionId]);

  return session;
}

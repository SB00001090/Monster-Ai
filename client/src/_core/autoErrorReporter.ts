import { createTRPCClient, httpBatchLink } from "@trpc/client";
import superjson from "superjson";
import type { AppRouter } from "../../../server/routers";
import { reportGuardianError } from "../lib/guardianApi";

type ClientAction =
  | { type: "guest" }
  | { type: "reload" }
  | { type: "redirect"; target: string };

const recentFingerprints = new Map<string, number>();
const DEBOUNCE_MS = 60_000;

let trpcClient: ReturnType<typeof createTRPCClient<AppRouter>> | null = null;

function getClient() {
  if (!trpcClient) {
    trpcClient = createTRPCClient<AppRouter>({
      links: [
        httpBatchLink({
          url: "/api/trpc",
          transformer: superjson,
          fetch(input, init) {
            return globalThis.fetch(input, {
              ...(init ?? {}),
              credentials: "include",
            });
          },
        }),
      ],
    });
  }
  return trpcClient;
}

function shouldReport(message: string, context: string): boolean {
  const key = `${message}|${context}`;
  const now = Date.now();
  const last = recentFingerprints.get(key);
  if (last && now - last < DEBOUNCE_MS) {
    return false;
  }
  recentFingerprints.set(key, now);
  return true;
}

export function applyClientAction(action?: ClientAction) {
  if (!action || typeof window === "undefined") return;
  switch (action.type) {
    case "guest": {
      if (!localStorage.getItem("guest_id")) {
        localStorage.setItem("guest_id", `guest_${Date.now()}`);
      }
      localStorage.setItem("guest_mode", "true");
      window.location.reload();
      break;
    }
    case "reload":
      window.location.reload();
      break;
    case "redirect":
      window.location.href = action.target;
      break;
    default:
      break;
  }
}

export async function reportError(
  error: unknown,
  context: string,
  source: "ui" | "trpc" | "api" | "global" = "ui"
) {
  if (typeof window === "undefined") return;

  const err = error instanceof Error ? error : new Error(String(error));
  if (!shouldReport(err.message, context)) return;

  try {
    const result = await getClient().errors.reportClientError.mutate({
      errorType: err.name || "Error",
      message: err.message,
      stack: err.stack,
      url: window.location.href,
      context,
      source,
    });

    if (result.clientAction) {
      const delay =
        result.clientAction.type === "guest" ? 1500 : 800;
      window.setTimeout(() => applyClientAction(result.clientAction), delay);
    }

    void reportGuardianError({
      errorType: err.name || "Error",
      message: err.message,
      stack: err.stack,
      context,
      source,
    }).catch(() => undefined);

    window.dispatchEvent(
      new CustomEvent("monster:auto-fix", {
        detail: result,
      })
    );
  } catch (reportErr) {
    console.warn("[AutoFix] Failed to report error:", reportErr);
  }
}
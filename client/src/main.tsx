import { trpc } from "@/lib/trpc";
import { UNAUTHED_ERR_MSG } from '@shared/const';
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { httpBatchLink, TRPCClientError } from "@trpc/client";
import { createRoot } from "react-dom/client";
import superjson from "superjson";
import App from "./App";
import { reportError } from "./_core/autoErrorReporter";
import { initSentry } from "./lib/sentry";
import { getLoginUrl } from "./const";
import "./index.css";
import './i18n/config';
import { toast } from "sonner";
import i18n from "./i18n/config";

// Ensure i18n is initialized before rendering

const queryClient = new QueryClient();

const redirectToLoginIfUnauthorized = (error: unknown) => {
  if (!(error instanceof TRPCClientError)) return;
  if (typeof window === "undefined") return;

  const isUnauthorized = error.message === UNAUTHED_ERR_MSG;

  if (!isUnauthorized) return;

  window.location.href = getLoginUrl();
};

const handleTrpcError = (error: unknown, context: string) => {
  if (error instanceof TRPCClientError && error.message === UNAUTHED_ERR_MSG) {
    redirectToLoginIfUnauthorized(error);
    return;
  }
  console.error(`[API Error] ${context}`, error);
  void reportError(error, context, "trpc");
};

queryClient.getQueryCache().subscribe(event => {
  if (event.type === "updated" && event.action.type === "error") {
    handleTrpcError(event.query.state.error, `query:${event.query.queryHash}`);
  }
});

queryClient.getMutationCache().subscribe(event => {
  if (event.type === "updated" && event.action.type === "error") {
    handleTrpcError(event.mutation.state.error, `mutation:${event.mutation.mutationId}`);
  }
});

if (typeof window !== "undefined") {
  window.addEventListener("monster:auto-fix", (ev) => {
    const detail = (ev as CustomEvent).detail as { fixAttempted?: boolean };
    if (detail?.fixAttempted) {
      toast.info(i18n.t("autoFix.toastFixing", "Reported — attempting auto-fix…"));
    } else {
      toast.info(i18n.t("autoFix.toastReported", "Error reported automatically."));
    }
  });

  window.addEventListener("error", (ev) => {
    void reportError(ev.error ?? ev.message, "window.onerror", "global");
  });

  window.addEventListener("unhandledrejection", (ev) => {
    void reportError(ev.reason, "unhandledrejection", "global");
  });
}

const trpcClient = trpc.createClient({
  links: [
    httpBatchLink({
      url: "/api/trpc",
      transformer: superjson,
      fetch(input, init) {
        const headers = new Headers(init?.headers);
        const guestMode = localStorage.getItem("guest_mode");
        const guestId = localStorage.getItem("guest_id");
        if (guestMode === "true" && guestId) {
          headers.set("x-guest-id", guestId);
        }
        return globalThis.fetch(input, {
          ...(init ?? {}),
          headers,
          credentials: "include",
        });
      },
    }),
  ],
});

void initSentry();

createRoot(document.getElementById("root")!).render(
  <trpc.Provider client={trpcClient} queryClient={queryClient}>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </trpc.Provider>
);

/** Cloudflare Pages — proxy /api/* → Monster AI Python backend */
interface Env {
  VITE_MONSTER_API_URL?: string;
  BACKEND_PYTHON_URL?: string;
}

export const onRequest: PagesFunction<Env> = async (context) => {
  const path = new URL(context.request.url).pathname;
  if (path.startsWith("/api/trpc") || path.startsWith("/api/oauth")) {
    return context.next();
  }
  const base = (
    context.env.VITE_MONSTER_API_URL ||
    context.env.BACKEND_PYTHON_URL ||
    ""
  ).replace(/\/$/, "");
  if (!base) {
    return new Response(
      JSON.stringify({
        error:
          "Set VITE_MONSTER_API_URL in Cloudflare Pages env (Tunnel → local :7860)",
      }),
      { status: 503, headers: { "content-type": "application/json" } },
    );
  }
  const url = new URL(context.request.url);
  let backendPath = url.pathname;
  if (backendPath === "/api/health") backendPath = "/health";
  else if (backendPath === "/api/status") backendPath = "/status";
  const target = `${base}${backendPath}${url.search}`;
  return fetch(target, context.request);
};
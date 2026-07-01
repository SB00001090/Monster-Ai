/** Cloudflare Pages — proxy /api/trpc → Monster AI Python (:7860 proxies to Node :3000) */
interface Env {
  BACKEND_NODE_URL?: string;
  VITE_MONSTER_NODE_URL?: string;
  VITE_MONSTER_API_URL?: string;
  BACKEND_PYTHON_URL?: string;
}

export const onRequest: PagesFunction<Env> = async (context) => {
  const base = (
    context.env.BACKEND_NODE_URL ||
    context.env.VITE_MONSTER_NODE_URL ||
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
  const target = `${base}${url.pathname}${url.search}`;
  return fetch(target, context.request);
};
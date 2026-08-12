// Reverse proxy: api.heartbox.tw -> Cloud Run.
//
// Cloud Run routes by Host header, so a plain proxied CNAME would 404. This
// worker rewrites Host to the run.app hostname and adds permissive CORS so the
// heartbox.tw frontend (a separate worker) can call it.
//
// Update BACKEND_* whenever the Cloud Run service is redeployed into a new
// GCP project — the run.app hostname embeds the project number.

const BACKEND_ORIGIN = "https://heartbox-api-521869298949.asia-east1.run.app";
const BACKEND_HOST = "heartbox-api-521869298949.asia-east1.run.app";

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }

    const url = new URL(request.url);
    const targetUrl = BACKEND_ORIGIN + url.pathname + url.search;
    const headers = new Headers(request.headers);
    headers.set("Host", BACKEND_HOST);

    const res = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.body,
      redirect: "manual",
    });

    const responseHeaders = new Headers(res.headers);
    Object.entries(corsHeaders(request)).forEach(([k, v]) => {
      responseHeaders.set(k, v);
    });

    return new Response(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    });
  },
};

function corsHeaders(request) {
  return {
    "Access-Control-Allow-Origin": request.headers.get("Origin") || "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept-Language",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Max-Age": "86400",
  };
}

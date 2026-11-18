// security-hardening / 复测整改证据 / 替代工具链保持页面与开发入口
import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { buildProduction, serveFrontend } from "../../frontend/toolchain.mjs";

test("production assets, deep links, dev/preview proxy and failure boundary", async () => {
  const seen = [];
  const backend = http.createServer(async (req, res) => {
    let body = "";
    for await (const part of req) body += part;
    seen.push({ path: req.url, method: req.method, token: req.headers["x-csrf-token"], body });
    res.writeHead(200, { "Content-Type": "application/json", "Set-Cookie": "synthetic=ok; HttpOnly" });
    res.end(JSON.stringify({ ok: true }));
  });
  await new Promise((resolve) => backend.listen(0, "127.0.0.1", resolve));
  try {
    await buildProduction();
    for (const mode of ["preview", "dev"]) {
      const app = await serveFrontend({ mode, port: 0, apiPort: backend.address().port });
      try {
        const base = `http://127.0.0.1:${app.port}`;
        const response = await fetch(base + "/assignments");
        assert.equal(response.status, 200);
        const html = await response.text();
        assert.match(html, /<div id="root"><\/div>/);
        assert.doesNotMatch(html, /src="\/src\/main.tsx"/);
        const script = /<script[^>]+src="([^"]+)"/.exec(html)[1];
        const css = /<link[^>]+href="([^"]+)"/.exec(html)[1];
        assert.equal((await fetch(base + script)).status, 200);
        assert.match(await (await fetch(base + css)).text(), /--red/);
        const write = await fetch(base + "/api/submissions/1/grade?test=1", {
          method: "POST", headers: { "X-CSRF-Token": "synthetic-test", "Content-Type": "application/json" }, body: "{}",
        });
        assert.equal(write.status, 200);
        assert.match(write.headers.get("set-cookie"), /HttpOnly/);
        assert.deepEqual(seen.at(-1), { path: "/api/submissions/1/grade?test=1", method: "POST", token: "synthetic-test", body: "{}" });
        assert.deepEqual(await (await fetch(base + "/health")).json(), { ok: true });
        // fetch normalizes Host; use the HTTP client to exercise the real header.
        const denied = await new Promise((resolve, reject) => {
          http.get(base, { headers: { Host: "untrusted.example" } }, (res) => {
            res.resume(); resolve(res.statusCode);
          }).on("error", reject);
        });
        assert.equal(denied, 403);
        assert.doesNotMatch(await (await fetch(base + "/..%2fpackage.json")).text(), /"private"\s*:\s*true/);
      } finally { await app.close(); }
    }
    const unused = backend.address().port;
    await new Promise((resolve) => backend.close(resolve));
    const app = await serveFrontend({ mode: "preview", port: 0, apiPort: unused });
    try {
      const response = await fetch(`http://127.0.0.1:${app.port}/api/missing`);
      assert.equal(response.status, 503);
      assert.deepEqual(await response.json(), { error: "unavailable" });
    } finally { await app.close(); }
  } finally { if (backend.listening) await new Promise((resolve) => backend.close(resolve)); }
});

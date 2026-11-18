import * as esbuild from "esbuild";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import http from "node:http";
import { isIP } from "node:net";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));

function options(development) {
  const outdir = path.join(root, development ? ".dev-dist" : "dist");
  return {
    absWorkingDir: root,
    entryPoints: ["src/main.tsx"],
    outdir,
    bundle: true,
    format: "esm",
    target: "es2022",
    jsx: "automatic",
    minify: !development,
    metafile: true,
    entryNames: development ? "assets/[name]" : "assets/[name]-[hash]",
    define: { "process.env.NODE_ENV": JSON.stringify(development ? "development" : "production") },
    banner: development ? { js: "new EventSource('/esbuild').addEventListener('change', () => location.reload());" } : {},
    plugins: [{
      name: "existing-html-entry",
      setup(build) {
        build.onEnd(async (result) => {
          if (result.errors.length) return;
          const [entry, metadata] = Object.entries(result.metafile.outputs)
            .find(([, value]) => value.entryPoint === "src/main.tsx");
          const asset = (name) => "/" + path.relative(outdir, path.resolve(root, name)).split(path.sep).join("/");
          let html = await readFile(path.join(root, "index.html"), "utf8");
          if (!html.includes('src="/src/main.tsx"')) throw new Error("Review changed HTML entry before building");
          html = html.replace('src="/src/main.tsx"', `src="${asset(entry)}"`);
          if (metadata.cssBundle) html = html.replace("</head>", `<link rel="stylesheet" href="${asset(metadata.cssBundle)}" /></head>`);
          await mkdir(outdir, { recursive: true });
          await writeFile(path.join(outdir, "index.html"), html);
        });
      },
    }],
  };
}

export async function buildProduction() {
  await esbuild.build(options(false));
}

export async function serveFrontend({ mode, port, host = "127.0.0.1", apiPort = 8080 }) {
  const development = mode === "dev";
  const ctx = await esbuild.context(development ? options(true) : {});
  try {
    if (development) await ctx.watch();
    const assets = await ctx.serve({
      host: "127.0.0.1", port: 0,
      servedir: path.join(root, development ? ".dev-dist" : "dist"),
      fallback: path.join(root, development ? ".dev-dist" : "dist", "index.html"),
    });
    const server = http.createServer((req, res) => {
      let hostname;
      try { hostname = new URL(`http://${req.headers.host}`).hostname.replace(/^\[|\]$/g, ""); }
      catch { res.writeHead(400).end(); return; }
      if (hostname !== "localhost" && !hostname.endsWith(".localhost") && !isIP(hostname)) {
        res.writeHead(403).end("Forbidden host"); return;
      }
      const pathname = (req.url || "/").split("?")[0];
      const api = pathname === "/api" || pathname.startsWith("/api/") || pathname === "/health";
      const upstream = http.request({
        host: "127.0.0.1", port: api ? apiPort : assets.port,
        path: req.url, method: req.method, headers: req.headers,
      }, (response) => {
        res.writeHead(response.statusCode, response.headers);
        response.pipe(res);
      });
      upstream.on("error", () => {
        if (res.headersSent) res.destroy();
        else res.writeHead(503, { "Content-Type": "application/json" }).end('{"error":"unavailable"}');
      });
      if (api) upstream.setTimeout(30_000, () => upstream.destroy());
      req.on("aborted", () => upstream.destroy());
      req.pipe(upstream);
    });
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(port, host, resolve);
    });
    return {
      port: server.address().port,
      async close() {
        server.closeAllConnections();
        await new Promise((resolve) => server.close(resolve));
        await ctx.dispose();
      },
    };
  } catch (error) {
    await ctx.dispose();
    throw error;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const mode = process.argv[2];
  if (mode === "build") await buildProduction();
  else if (mode === "dev" || mode === "preview") {
    const args = process.argv.slice(3);
    let port = mode === "dev" ? 5173 : 4173;
    let host = "127.0.0.1";
    for (let i = 0; i < args.length; i++) {
      if (args[i] === "--port") port = Number(args[++i]);
      else if (args[i] === "--host") host = args[++i] || "0.0.0.0";
      else throw new Error("Supported options: --host <host> --port <port>");
    }
    if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error("Invalid port");
    const app = await serveFrontend({ mode, port, host });
    console.log(`Frontend: http://${host}:${app.port}`);
    for (const signal of ["SIGINT", "SIGTERM"]) process.once(signal, async () => { await app.close(); process.exit(0); });
  } else throw new Error("Expected build, dev or preview");
}

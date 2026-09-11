import { readFile, writeFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(root, "dist-pages");
const demo = {
  mode: "demo",
  apiUrl: "",
  cognitoDomain: "",
  clientId: "",
  scope: "",
};
// Always overwrite the Pages artifact with a public, browser-only configuration.
// AWS CodeBuild continues to publish its separate dist/ directory with live config.
await writeFile(resolve(output, "config.json"), JSON.stringify(demo, null, 2) + "\n");
await writeFile(resolve(output, ".nojekyll"), "");
const html = await readFile(resolve(output, "index.html"), "utf8");
if (!html.includes('/threatlens/assets/') || /(?:src|href)="\/assets\//.test(html)) {
  throw new Error("Pages assets must use the /threatlens/ base path");
}
const bundles = (await readdir(resolve(output, "assets"))).filter(name => name.endsWith(".js"));
const source = (await Promise.all(bundles.map(name => readFile(resolve(output, "assets", name), "utf8")))).join("\n");
if (!source.includes("/threatlens/") || !source.includes("config.json")) {
  throw new Error("Missing base-aware runtime configuration loading");
}
console.log("PASS: Pages artifact uses /threatlens/, browser-only demo configuration and separate dist-pages/ output");

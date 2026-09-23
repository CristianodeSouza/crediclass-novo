import { build } from "vite";
import { resolve } from "node:path";

await build({
  configFile: false,
  root: process.cwd(),
  build: {
    lib: {
      entry: resolve("frontend/editor/main.js"),
      name: "CrediclassEditor",
      formats: ["iife"],
      fileName: () => "crediclass-editor.js",
    },
    outDir: resolve("backend/static/vendor"),
    emptyOutDir: false,
    minify: true,
  },
});

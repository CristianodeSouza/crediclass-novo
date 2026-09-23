import { defineConfig } from "vite";

export default defineConfig({
  build: {
    lib: {
      entry: "frontend/editor/main.js",
      name: "CrediclassEditor",
      formats: ["iife"],
      fileName: () => "crediclass-editor.js",
    },
    outDir: "backend/static/vendor",
    emptyOutDir: false,
    minify: true,
  },
});

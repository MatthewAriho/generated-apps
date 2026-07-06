import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  base: "/bookworm/",
  build: {
    outDir: "../nginx/dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/covers": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});

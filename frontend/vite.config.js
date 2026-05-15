import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api/inventory": {
        target: "http://backend-inventory:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/inventory/, "/api"),
      },
      "/api/pos": {
        target: "http://backend-pos:3000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/pos/, "/api"),
      },
    },
  },
});

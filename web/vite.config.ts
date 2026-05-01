import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";

export default defineConfig({
  plugins: [TanStackRouterVite({ autoCodeSplitting: true }), react()],
  server: {
    proxy: {
      "/v1": "http://localhost:8000",
      "/healthz": "http://localhost:8000",
      "/openapi.json": "http://localhost:8000",
      "/docs": "http://localhost:8000",
      "/redoc": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});

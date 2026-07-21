import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

// M36.1 WP4B F06 — the smallest maintainable harness that can execute React
// provider/component behavior (Context effects, hook state transitions),
// which node's built-in test runner (used by test:pure for plain-function
// tests) cannot do. Scoped to tests/**; test:pure's existing pure-function
// tests are untouched and still run separately via node --test.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.tsx", "tests/**/*.test.ts"],
    setupFiles: ["./tests/setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});

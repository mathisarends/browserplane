import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/browser",
  timeout: 60000,
  expect: { timeout: 10000 },
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:15173",
    channel: process.platform === "win32" ? "chrome" : undefined,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm exec vite -- --config vite.config.ts --host 127.0.0.1 --port 15173",
    url: "http://127.0.0.1:15173",
    env: { BROWSERPLANE_API_URL: "http://127.0.0.1:18000" },
  },
});

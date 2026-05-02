import { defineConfig, devices } from '@playwright/test';

// Port 3000 may be occupied by another local app; default to 3001 for E2E.
// Override at any time: PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run test:e2e
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3001';
const PORT = new URL(BASE_URL).port || '3001';

export default defineConfig({
  testDir: './e2e',
  tsconfig: './e2e/tsconfig.json',
  timeout: 90_000,       // full flow (AI calls + file upload) can take ~60s
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Start the Next.js dev server automatically when running locally */
  webServer: process.env.CI
    ? undefined
    : {
        command: `npm run dev -- -p ${PORT}`,
        url: BASE_URL,
        reuseExistingServer: true,
        timeout: 120_000,
      },
});

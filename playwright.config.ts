import { defineConfig, devices } from '@playwright/test';

/**
 * ZONATA / URA Enterprise — Playwright Browser End-to-End Configuration
 * Qualified for Public GA Release Verification
 */
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 45 * 1000,
  expect: {
    timeout: 10 * 1000
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Sequential execution to prevent tenant contention
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/playwright-results.json' }],
    ['html', { outputFolder: 'test-results/playwright-report', open: 'never' }]
  ],
  use: {
    baseURL: process.env.BASE_URL || 'https://zonata-staging.onrender.com',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: 'chromium-desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: 'chromium-mobile',
      use: {
        ...devices['Pixel 7'],
      },
    },
  ],
});

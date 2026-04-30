import { test, expect } from '@playwright/test';
import path from 'path';

const EMAIL = process.env.E2E_TEST_EMAIL ?? '';
const PASSWORD = process.env.E2E_TEST_PASSWORD ?? '';
const FIXTURE_CSV = path.join(__dirname, 'fixtures', 'demo-inventory.csv');

test.describe('StockWise happy-path demo', () => {
  test('full demo flow: login → upload → dashboard → simulate → explain → export', async ({
    page,
  }, testInfo) => {
    // Skip gracefully if credentials not provided — test.skip() must be called
    // in the test body (not beforeEach) to actually halt execution.
    testInfo.skip(!EMAIL || !PASSWORD, 'Set E2E_TEST_EMAIL and E2E_TEST_PASSWORD to run this test');

    // ── 1. Login ────────────────────────────────────────────────────────────
    await page.goto('/login');
    // Wait for the login form to be fully ready before filling
    await page.locator('[data-testid="email-input"]').waitFor({ state: 'visible' });
    await page.locator('[data-testid="email-input"]').fill(EMAIL);
    await page.locator('[data-testid="password-input"]').fill(PASSWORD);
    await page.locator('[data-testid="login-submit"]').click();
    await page.waitForURL('/', { timeout: 15_000 });

    // ── 2. Select CSV upload mode ────────────────────────────────────────────
    await page.locator('[data-testid="csv-upload-card"]').click();
    await expect(page.locator('[data-testid="csv-file-input"]')).toBeAttached();

    // ── 3. Upload CSV fixture ────────────────────────────────────────────────
    // Set the file on the hidden input directly — avoids OS file dialog
    await page.locator('[data-testid="csv-file-input"]').setInputFiles(FIXTURE_CSV);
    await page.waitForURL(/\/dashboard\//, { timeout: 30_000 });

    // ── 4. Dashboard loads with KPI cards ────────────────────────────────────
    const kpiCards = page.locator('[data-testid="kpi-cards"]');
    await expect(kpiCards).toBeVisible();
    // At least one KPI value should be non-zero (items were uploaded)
    const firstKpiValue = kpiCards.locator('.text-2xl').first();
    await expect(firstKpiValue).not.toHaveText('0');

    // ── 5. Decision Brief appears ────────────────────────────────────────────
    const decisionBrief = page.locator('[data-testid="decision-brief"]');
    await expect(decisionBrief).toBeVisible({ timeout: 20_000 });
    // Brief should have some non-empty text (AI or fallback)
    await expect(decisionBrief).not.toBeEmpty();

    // ── 6. Items table rendered ──────────────────────────────────────────────
    await expect(page.locator('[data-testid="items-table"]')).toBeVisible();

    // ── 7. Click Simulate on first item ──────────────────────────────────────
    const firstSimulateBtn = page.locator('[data-testid="simulate-btn"]').first();
    await expect(firstSimulateBtn).toBeVisible();
    await firstSimulateBtn.click();
    await page.waitForURL(/\/simulation\//, { timeout: 15_000 });

    // ── 8. Simulation page: fill qty and run ──────────────────────────────────
    const qtyInput = page.locator('[data-testid="reorder-qty-input"]');
    await expect(qtyInput).toBeVisible();
    await qtyInput.fill('50');

    await page.locator('[data-testid="run-simulation-btn"]').click();

    // Result card appears
    const simResult = page.locator('[data-testid="simulation-result"]');
    await expect(simResult).toBeVisible({ timeout: 15_000 });

    // ── 9. View Explanation ──────────────────────────────────────────────────
    const explainBtn = page.locator('[data-testid="view-explanation-btn"]');
    await expect(explainBtn).toBeVisible();
    await explainBtn.click();
    await page.waitForURL(/\/explanation\//, { timeout: 15_000 });

    // Explanation content shown (AI or deterministic fallback — either is fine)
    const explanationContent = page.locator('[data-testid="explanation-content"]');
    await expect(explanationContent).toBeVisible({ timeout: 20_000 });
    await expect(explanationContent).not.toBeEmpty();

    // ── 10. Export CSV ────────────────────────────────────────────────────────
    // Click "Back to Dashboard" link on the explanation page — more reliable than
    // page.goBack() with Next.js client-side routing.
    await page.locator('a', { hasText: /back to dashboard/i }).first().click();
    await page.waitForURL(/\/dashboard\//, { timeout: 15_000 });

    const exportLink = page.locator('[data-testid="export-report-link"]');
    await expect(exportLink).toBeVisible();
    await exportLink.click();
    await page.waitForURL(/\/export\//, { timeout: 10_000 });

    // Wait for the export button then trigger download
    const exportCsvBtn = page.locator('[data-testid="export-csv-btn"]');
    await expect(exportCsvBtn).toBeVisible();

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15_000 }),
      exportCsvBtn.click(),
    ]);

    expect(download.suggestedFilename()).toMatch(/\.csv$/);
  });
});

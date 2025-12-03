import { chromium } from "playwright";
import assert from "node:assert/strict";
const browser = await chromium.launch({
  headless: true,
  ...(process.env.CHROME ? { executablePath: process.env.CHROME } : {}),
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
page.setDefaultTimeout(5000);
try {
  await page.goto(process.env.APP_URL || "http://127.0.0.1:18130");
  await page.getByLabel("Access key").fill(process.env.OPERATOR_TOKEN);
  await page.getByRole("button", { name: "Open supplier desk" }).click();
  await page.getByRole("heading", { name: "Supplier cases" }).waitFor();
  assert.equal(
    await page.locator("body").evaluate((e) => e.scrollWidth > innerWidth),
    false,
  );
  const tax = "UI-" + Date.now();
  await page.getByRole("button", { name: "New supplier" }).click();
  await page.getByLabel("Legal name").fill("Northstar Components");
  await page.getByLabel("Tax identifier").fill(tax);
  await page
    .getByLabel("Goods or services")
    .fill("Industrial bearings and machine parts");
  await page.getByRole("button", { name: "Start checks" }).click();
  await page
    .getByRole("heading", { name: "Northstar Components", exact: true })
    .waitFor();
  await page
    .locator(".status-banner")
    .filter({ hasText: "Tax certificate needed" })
    .waitFor();
  await page.getByLabel("Certificate tax identifier").fill(tax);
  await page.getByRole("button", { name: "Provide tax certificate" }).click();
  await page
    .locator(".status-banner")
    .filter({ hasText: "Ready for independent review" })
    .waitFor();
  await page
    .getByRole("heading", { name: "Proposed supplier record" })
    .waitFor();
  await page.getByRole("heading", { name: "Evidence trail" }).waitFor();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByLabel("Access key").fill(process.env.REVIEWER_TOKEN);
  await page.getByRole("button", { name: "Open supplier desk" }).click();
  await page.locator(".case-item").filter({ hasText: tax }).click();
  await page.getByRole("button", { name: "Approve this exact record" }).click();
  await page
    .locator(".status-banner")
    .filter({ hasText: "Supplier onboarded" })
    .waitFor();
  assert.equal(
    await page.evaluate(() => localStorage.length + sessionStorage.length),
    0,
  );
  if (process.env.SCREENSHOT)
    await page.screenshot({ path: process.env.SCREENSHOT, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(
    await page.locator("body").evaluate((e) => e.scrollWidth > innerWidth),
    false,
  );
  console.log(
    JSON.stringify({
      login: "passed",
      create: "passed",
      resume: "passed",
      approval: "passed",
      mobile: "passed",
      tax,
    }),
  );
} finally {
  await browser.close();
}

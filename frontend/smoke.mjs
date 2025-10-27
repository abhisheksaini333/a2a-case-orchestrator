import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true,...(process.env.CHROME?{executablePath:process.env.CHROME}:{})});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
try {
 await page.goto(process.env.APP_URL||'http://127.0.0.1:18130');
 await page.getByLabel('Access key').fill(process.env.OPERATOR_TOKEN);
 await page.getByRole('button',{name:'Open supplier desk'}).click();
 await page.getByRole('heading',{name:'Supplier cases'}).waitFor();
 assert.equal(await page.locator('body').evaluate(e=>e.scrollWidth>innerWidth),false);
 console.log(JSON.stringify({login:'passed'}));
} finally {await browser.close();}

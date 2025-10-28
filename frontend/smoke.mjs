import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true,...(process.env.CHROME?{executablePath:process.env.CHROME}:{})});
const page=await browser.newPage({viewport:{width:1440,height:1000}});
page.setDefaultTimeout(5000);
try {
 await page.goto(process.env.APP_URL||'http://127.0.0.1:18130');
 await page.getByLabel('Access key').fill(process.env.OPERATOR_TOKEN);
 await page.getByRole('button',{name:'Open supplier desk'}).click();
 await page.getByRole('heading',{name:'Supplier cases'}).waitFor();
 assert.equal(await page.locator('body').evaluate(e=>e.scrollWidth>innerWidth),false);
 const tax='UI-'+Date.now();
 await page.getByRole('button',{name:'New supplier'}).click();
 await page.getByLabel('Legal name').fill('Northstar Components');
 await page.getByLabel('Tax identifier').fill(tax);
 await page.getByLabel('Goods or services').fill('Industrial bearings and machine parts');
 await page.getByRole('button',{name:'Start checks'}).click();
 await page.getByRole('heading',{name:'Northstar Components',exact:true}).waitFor();
 await page.locator('.status-banner').filter({hasText:'Tax certificate needed'}).waitFor();
 console.log(JSON.stringify({login:'passed',create:'passed',tax}));
} finally {await browser.close();}

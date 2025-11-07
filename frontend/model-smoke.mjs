import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true,...(process.env.CHROME?{executablePath:process.env.CHROME}:{})});
try{
 const page=await browser.newPage();page.setDefaultTimeout(10000);
 await page.goto(process.env.APP_URL||'http://127.0.0.1:18130');
 await page.getByLabel('Access key').fill(process.env.OPERATOR_TOKEN);await page.getByRole('button',{name:'Open supplier desk'}).click();
 await page.getByRole('button',{name:'New supplier'}).click();await page.getByText('Paste an intake note',{exact:true}).click();
 await page.getByLabel('Intake note').fill('Please onboard Northstar Parts with tax identifier NP-202. They supply industrial bearings.');
 await page.getByLabel('Extraction mode').selectOption('local-model');await page.getByRole('button',{name:'Extract draft fields'}).click();
 await page.getByText('Fields extracted. Review them before starting checks.',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Legal name').inputValue(),'Northstar Parts');assert.equal(await page.getByLabel('Tax identifier',{exact:true}).inputValue(),'NP-202');
 console.log(JSON.stringify({actual_local_model_preview:'passed',auto_submission:false}));
}finally{await browser.close()}

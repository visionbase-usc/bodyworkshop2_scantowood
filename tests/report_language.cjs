const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const elements = new Map();
const element = () => ({textContent:'', addEventListener(){}, setAttribute(){}, replaceChildren(){}, append(){}});
const get = id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);};
const buttons = ['zh', 'ja', 'en'].map(lang => ({dataset:{lang}, setAttribute(){}, addEventListener(type, fn){this.click = fn;}}));
const context = vm.createContext({document:{getElementById:get, createElement:element, documentElement:{}, querySelectorAll:s => s === '[data-lang]' ? buttons : []},
  navigator:{language:'zh-TW'}, localStorage:{getItem:()=>null, setItem(){}}, location:{protocol:'https:'},
  addEventListener(){}, fetch:async()=>({json:async()=>null}), Worker:class{}, URL, Blob});
(async()=>{
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8'), context);
  await new Promise(resolve=>setImmediate(resolve));
  get('form').up_axis = {value:'z'};
  vm.runInContext('lastReport = {warnings:[], warnings_en:[]}; reportTexts = {original:"# 組裝報告", en:"# Assembly report"};', context);
  for (const lang of ['en','zh','ja','en']) {
    buttons.find(b=>b.dataset.lang === lang).click();
    assert.match(get('report').innerHTML, lang === 'en' ? /Assembly report/ : /組裝報告/);
  }
  vm.runInContext('setResult(false);',context);
  buttons[2].click();
  console.log('Report language switching after computation: passed');
})().catch(error=>{console.error(error);process.exitCode=1;});

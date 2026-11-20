// Offline regression for the endpoint-rounding bug found during browser testing.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, 'viewer_1093.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0];
const elements = new Map();
const document = {createElement() {return {children:[],style:{},append(...items){this.children.push(...items);}};}, getElementById(id) {
  if (!elements.has(id)) elements.set(id, {value:'',children:[],addEventListener(){},append(...items){this.children.push(...items);},replaceChildren(){this.children=[];}});
  return elements.get(id);
}};
const context = vm.createContext({document, console});
vm.runInContext(script, context);
vm.runInContext('const originalDraw=draw;',context);
const header = 'canonical_event_id,provider,instrument,band,hjd,magnitude,magnitude_error,native_fields_json\r\n';
context.fixtureCSV = header + [
  'OGLE-2016-BLG-1093,ogle,OGLE,I,2455260.86866000,19.2,0.1,"{""Inst"":""OGLE""}"',
  'OGLE-2016-BLG-1093,kmtnet,KMTA,I,2457681.28989000,18.2,0.1,{}',
  'OGLE-2016-BLG-1093,spitzer,Spitzer,L,2457557.95857000,16.2,0.1,{}',
].join('\r\n')+'\r\n';
assert.equal(vm.runInContext('load(fixtureCSV).length', context), 3);
assert.equal(vm.runInContext('load(fixtureCSV)[0].native_fields_json',context),' {"Inst":"OGLE"}'.trim());
vm.runInContext('rows=load(fixtureCSV); draw=()=>{}; full();', context);
context.first = Number(elements.get('start').value);
context.last = Number(elements.get('end').value);
assert.equal(vm.runInContext('rows.filter(r=>r.t>=first && r.t<=last).length',context),3);
context.fixtureCSV += 'OGLE-2016-BLG-1093,moa,MOA,R,2457560.5,16.8,0.02,{}\r\n';
assert.equal(vm.runInContext('load(fixtureCSV).filter(r=>r.provider==="moa").length',context),1);
vm.runInContext('rows=load(fixtureCSV);draw=originalDraw;full();',context);
assert.equal(elements.get('plots').children.length,4);
assert.match(elements.get('plots').children[3].children[0].textContent,/MOA/);
context.fixtureCSV = context.fixtureCSV.replaceAll('OGLE-2016-BLG-1093','OGLE-2016-BLG-1190');
assert.throws(()=>vm.runInContext('load(fixtureCSV)',context),/Wrong event/);
console.log('Viewer CSV quoting, exact full-range endpoints and wrong-event rejection passed.');

if(process.argv[2]){context.fixtureCSV=fs.readFileSync(process.argv[2],'utf8');vm.runInContext('rows=load(fixtureCSV);full();',context);const points=elements.get('plots').children.flatMap(s=>s.children).reduce((n,e)=>n+((e.innerHTML||'').match(/<circle /g)||[]).length,0);assert.equal(points,10728);assert.equal(elements.get('plots').children.length,4);console.log('All 10,728 real-file points render across four panels.');}

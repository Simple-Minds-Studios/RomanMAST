// Validate the bundled public example and graceful load failure independently of network availability.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'viewer_1093.html'),'utf8');
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'data/1093.json'),'utf8'));
const elements=new Map();const make=()=>({children:[],style:{},value:'',hidden:true,disabled:false,addEventListener(){},append(...v){this.children.push(...v);},replaceChildren(){this.children=[];}});
const document={baseURI:'https://example.test/examples/public_data/viewer_1093.html',createElement:make,getElementById(id){if(!elements.has(id))elements.set(id,make());return elements.get(id);}};
const context=vm.createContext({document,console,URL,AbortController,setTimeout,clearTimeout,window:{location:{hash:'',protocol:'https:'}}});
vm.runInContext(html.split('<script>')[1].split('</script>')[0],context);context.data=data;
assert.equal(vm.runInContext('loadDemoRows(data).length',context),10728);
for(const change of [d=>{d.event_id='wrong';},d=>{d.rows.pop();},d=>{d.rows[1][4]=d.rows[0][4];},d=>{d.rows[0][2]='nan';},d=>{d.rows[0][0]='unknown';}]){
 const copy=structuredClone(data);change(copy);context.corrupt=copy;assert.throws(()=>vm.runInContext('loadDemoRows(corrupt)',context));
}
(async()=>{
 context.fetch=async()=>({ok:true,json:async()=>data});
 await vm.runInContext('loadExample()',context);
 assert.equal(elements.get('controls').hidden,false);
 assert.equal(elements.get('plots').children.length,4);
 assert.match(elements.get('status').textContent,/10,728/);
 assert.equal(elements.get('demo').disabled,false);
 const panels=elements.get('plots').children;
 context.fetch=async()=>{throw Error('offline');};
 await vm.runInContext('loadExample()',context);
 assert.match(elements.get('status').textContent,/Could not load/);
 assert.equal(elements.get('demo').disabled,false);
 assert.equal(elements.get('plots').children,panels);
 console.log('Public example identity, record counts, corrupt-data rejection, loading and failure recovery passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});

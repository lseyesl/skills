const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync(require('path').join(__dirname,'../assets/annotation-editor.html'),'utf8').split('<script>')[1].split('</script>')[0];
function setup(){const elements={};const context=new Proxy({},{get:()=>()=>{}});function element(){return {value:'',options:[],files:[],replaceChildren(){this.options=[]},append(o){this.options.push(o)},getContext(){return context},getBoundingClientRect(){return {left:0,top:0,width:8,height:6}},setPointerCapture(){},click(){s.downloads++}}}let s={downloads:0,document:{getElementById(id){return elements[id]??=element()},createElement:element},Image:class{},URL:{createObjectURL(){return 'blob:test'},revokeObjectURL(){}},Blob:class{},setTimeout(){},prompt(){return 'newpart'}};vm.createContext(s);vm.runInContext(source,s);vm.runInContext("c.width=8;c.height=6;$('mode').value='polygons'",s);return s}

const assert=require('assert');
function run(code){const context=setup();return vm.runInContext(code,context)}
assert.strictEqual(run("data.parts=[{id:'subject',node:null,z_index:0,visible:{polygons:[]}}];refresh();reg()===data.subject"),true);
assert.strictEqual(run("im.width=8;im.height=6;im.naturalWidth=8;loadedHash='new';data.source_size=[8,6];data.source_sha256='old';$('export').onclick();downloads"),0);
assert.strictEqual(run("im.width=8;im.height=6;im.naturalWidth=8;loadedHash='same';loadedName='source.png';data.source_size=[8,6];data.source_sha256='same';$('export').onclick();downloads"),1);
assert.strictEqual(run("im.width=8;im.height=6;im.naturalWidth=8;loadedHash='new';loadedName='new.png';data.source_size=[8,6];data.source_sha256='old';$('bind').onclick();$('export').onclick();data.source==='new.png'&&data.source_sha256==='new'&&downloads===1"),true);
console.log('EDITOR_CONTRACT_OK');

assert.strictEqual(run("im.width=8;im.height=6;im.naturalWidth=8;loadedHash='same';loadedName='actual.png';data.source='missing.png';data.source_size=[8,6];data.source_sha256='same';$('export').onclick();downloads"),0);

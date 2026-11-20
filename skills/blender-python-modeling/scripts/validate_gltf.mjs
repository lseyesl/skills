// Own adapter around the externally installed Khronos validator; no plugin code vendored.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const [assetArg, reportArg, moduleArg] = process.argv.slice(2);
const asset = await fs.realpath(assetArg);
const reportPath = path.resolve(reportArg);
const blocked = [];
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
let report;
try {
  const require = createRequire(import.meta.url);
  const validator = require(path.resolve(moduleArg));
  const data = await fs.readFile(asset);
  const root = path.dirname(asset);
  const files = {[asset]: sha(data)};
  const result = await validator.validateBytes(new Uint8Array(data), {
    uri:path.basename(asset),
    externalResourceFunction:async uri => {
      try {
        if (/^[a-z][a-z0-9+.-]*:/i.test(uri)) throw new Error('remote resource');
        const file = await fs.realpath(path.resolve(root,decodeURIComponent(uri)));
        const relative = path.relative(root,file);
        if (relative.startsWith('..'+path.sep) || relative === '..' || path.isAbsolute(relative)) throw new Error('resource outside delivery directory');
        const bytes = await fs.readFile(file);files[file] = sha(bytes);
        return new Uint8Array(bytes);
      } catch (error) {blocked.push({uri,reason:String(error)});throw error;}
    }
  });
  report = {schema_version:1,tool:'gltf-validator',version:validator.version(),node_version:process.version,input_sha256:sha(data),
            resource_fingerprints:files,status:blocked.length?'blocked':result.issues.numErrors?'failed':'passed',
            scope:'format/data checks only; no visual, consumer compatibility or optimization approval',blocked_resources:blocked,result};
} catch (error) {
  report = {schema_version:1,status:'blocked',reason:String(error),scope:'validator did not complete'};
}
await fs.writeFile(reportPath,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:report.status,report:reportPath}));
process.exitCode = report.status==='passed'?0:report.status==='failed'?1:2;

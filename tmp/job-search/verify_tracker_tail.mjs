import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const input = await FileBlob.load('outputs/01a07a13-0189-70c1-a1a4-d8e4c1f7d8e0/Yuxuan_Chen_Job_Application_Tracker.xlsx');
const wb = await SpreadsheetFile.importXlsx(input);
const check = await wb.inspect({kind:'table', range:'Applications!A242:W242', include:'values,formulas', tableMaxRows:3, tableMaxCols:23});
console.log(check.ndjson);
const errors = await wb.inspect({kind:'match', searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options:{useRegex:true,maxResults:100}, summary:'final formula error scan'});
console.log(errors.ndjson);
const preview = await wb.render({sheetName:'Applications', range:'A242:W242', scale:1, format:'png'});
await fs.writeFile('tmp/job-search/tracker-tail-preview.png', new Uint8Array(await preview.arrayBuffer()));

import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const records = JSON.parse(await fs.readFile(new URL("./tracker-data.json", import.meta.url), "utf8"));
const outputPath = "/Users/melc/Documents/Intern/LLM Search Optimizer/geo-engine/outputs/01a07a13-0189-70c1-a1a4-d8e4c1f7d8e0/Yuxuan_Chen_Job_Application_Tracker.xlsx";
const previewPath = "/Users/melc/Documents/Intern/LLM Search Optimizer/geo-engine/tmp/job-search/tracker-preview.png";
const wb = Workbook.create();
const ws = wb.worksheets.add("Applications");
ws.showGridLines = false;
ws.tabColor = "#1F4E78";

ws.getRange("A2").values = [["Job application tracker"]];
ws.getRange("A2").format.font = { name: "Arial", size: 14, bold: true, color: "#1F2937" };
ws.getRange("A3:W3").format.borders = { bottom: { style: "thin", color: "#1F4E78" } };
ws.getRange("A5:H5").values = [["Discovered", "In progress", "Ready", "Submitted", "Needs input", "Halted", "Total", "Last updated"]];
ws.getRange("A6:G6").formulas = [[
  '=COUNTIF($I$10:$I$509,"Discovered")',
  '=COUNTIF($I$10:$I$509,"In progress")',
  '=COUNTIF($I$10:$I$509,"Ready for application")',
  '=COUNTIF($I$10:$I$509,"Submitted")',
  '=COUNTIF($I$10:$I$509,"Needs input")',
  '=COUNTIF($I$10:$I$509,"Halted")',
  '=COUNTA($A$10:$A$509)'
]];
ws.getRange("H6").values = [[new Date()]];
ws.getRange("A5:H5").format = { fill: "#DCE6F1", font: { name: "Arial", size: 10, bold: true, color: "#1F2937" }, horizontalAlignment: "center" };
ws.getRange("A6:H6").format = { font: { name: "Arial", size: 10, bold: true, color: "#1F2937" }, horizontalAlignment: "center" };
ws.getRange("H6").setNumberFormat("mm/dd/yy h:mm AM/PM");

const headers = ["Company","Job title","LinkedIn URL","Official application URL","Date posted","Date discovered","Application started","Application submitted","Application status","Salary minimum","Salary maximum","SOC code","SOC title","Wage level analysis","Preferred location selected","Other locations","Work mode","Sponsorship info","Fit rating","Fit rationale","Resume version used","Questions needing input","Notes"];
ws.getRange("A9:W9").values = [headers];
ws.getRange("A9:W9").format = { fill: "#1F4E78", font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { insideVertical: { style: "thin", color: "#FFFFFF" } } };
ws.getRange("A9:W9").format.rowHeight = 34;

if (records.length) {
  const rows = records.map(r => headers.map(h => r[h] ?? null));
  ws.getRangeByIndexes(9, 0, rows.length, headers.length).values = rows;
}
ws.getRange("E10:H509").setNumberFormat("mm/dd/yy");
ws.getRange("J10:K509").setNumberFormat("$#,##0");
ws.getRange("A10:W509").format = { font: { name: "Arial", size: 10, color: "#1F2937" }, verticalAlignment: "top" };
ws.getRange("N10:W509").format.wrapText = true;
ws.getRange("I10:I509").dataValidation = { rule: { type: "list", values: ["Discovered","In progress","Needs input","Ready for application","Submitted","Halted","Rejected","Withdrawn"] } };
ws.getRange("I10:I509").conditionalFormats.add("containsText", { text: "Ready for application", format: { fill: "#DDEBF7", font: { color: "#1F4E78", bold: true } } });
ws.getRange("I10:I509").conditionalFormats.add("containsText", { text: "Submitted", format: { fill: "#E2F0D9", font: { color: "#2F6B2F", bold: true } } });
ws.getRange("I10:I509").conditionalFormats.add("containsText", { text: "Needs input", format: { fill: "#FFF2CC", font: { color: "#7F6000", bold: true } } });
ws.getRange("I10:I509").conditionalFormats.add("containsText", { text: "Halted", format: { fill: "#FCE4D6", font: { color: "#9C0006", bold: true } } });
ws.freezePanes.freezeRows(9);
ws.freezePanes.freezeColumns(2);
const widths = [20,30,26,28,13,13,13,13,16,15,15,12,28,42,24,28,14,24,12,44,22,38,44];
widths.forEach((width, i) => ws.getRangeByIndexes(0, i, 509, 1).format.columnWidth = width);
if (records.length) ws.tables.add(`A9:W${9 + records.length}`, true, "ApplicationsTable").style = "TableStyleMedium2";

wb.recalculate();
const check = await wb.inspect({ kind: "table", range: "Applications!A2:W12", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 23 });
console.log(check.ndjson);
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const preview = await wb.render({ sheetName: "Applications", range: "A1:W14", scale: 1, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(outputPath);
console.log(outputPath);

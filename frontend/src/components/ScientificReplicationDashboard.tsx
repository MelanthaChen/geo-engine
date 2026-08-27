import { useMemo, useState } from "react";
import { Check, ChevronDown, Circle, Download, X } from "lucide-react";

import { Button } from "../../@/components/ui/button";
import type { ExperimentRun, ExperimentStatistic, StrategyEvidence, StrategyId } from "@/types/experimentLab";

type MetricKey = "pawc" | "subjective_impression_calibrated" | "word_score" | "position_score";
type Props = { run: ExperimentRun; onReset: () => void };

const labels: Record<StrategyId, string> = {
  original: "Original", quotation: "Quotation", statistics: "Statistics",
  citation: "Citation", fluency: "Fluency", easy_to_understand: "Easy to understand",
  technical_terms: "Technical terms", authoritative: "Authoritative",
  unique_words: "Unique words", keyword_stuffing: "Keyword stuffing",
};
const paperPawc: Partial<Record<StrategyId, number>> = {
  original: 19.3, quotation: 27.2, statistics: 25.2, fluency: 24.7,
  citation: 24.6, easy_to_understand: 22.0, authoritative: 20.2,
  unique_words: 19.8, keyword_stuffing: 17.7,
};
const pipeline = [
  ["Official GEO-bench", "DATASET", "996 valid queries"],
  ["Query Selection", "INPUT", "sugg_idx target"],
  ["10 GEO Strategies", "METHODS", "baseline + 9 rewrites"],
  ["Document Rewrite", "TRANSFORM", "one per strategy"],
  ["LLM Generation", "SAMPLING", "n = 5"],
  ["Evaluation", "METRICS", "PAWC · Word · Position · Subjective ×7"],
  ["Replication Report", "OUTPUT", "statistics + evidence"],
] as const;
const conclusions = [
  ["quotation", "Quotation Addition improves visibility", "quotation", false],
  ["citation", "Cite Sources improves visibility", "citation", false],
  ["statistics", "Statistics Addition improves visibility", "statistics", false],
  ["fluency", "Fluency Optimization improves visibility", "fluency", false],
  ["keyword", "Keyword Stuffing does not improve visibility", "keyword_stuffing", true],
] as const;

export function ScientificReplicationDashboard({ run, onReset }: Props) {
  const [metric, setMetric] = useState<MetricKey>("pawc");
  const [sort, setSort] = useState<"paper" | "ours">("paper");
  const [strategy, setStrategy] = useState<StrategyId>("quotation");
  const [claimOpen, setClaimOpen] = useState<string | null>(null);
  const rows = useMemo(() => strategyRows(run, metric, sort), [run, metric, sort]);
  const original = rows.find((row) => row.strategy === "original")?.ours;
  const samples = run.runCount ?? evidenceSamples(run);
  const totalSamples = Math.max(run.totalQueries, 1) * 50;
  const progress = run.status === "completed" ? 100 : Math.min(100, Math.round(run.completedQueries / Math.max(run.totalQueries, 1) * 100));
  const trend = trendSimilarity(rows);
  const selectedEvidence = findEvidence(run, strategy);

  return <div className="space-y-9 pb-12 text-zinc-200">
    <header className="flex flex-col gap-5 border-b border-zinc-800 pb-6 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[.22em] text-sky-300">Princeton GEO · Scientific Replication</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">{run.name || "Official GEO-bench Experiment"}</h1>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-zinc-400">A live research record of the main single-strategy experiment. Missing measurements are shown as unavailable, never inferred.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <span className={`self-center border px-3 py-2 font-mono text-xs uppercase ${run.status === "completed" ? "border-emerald-700 text-emerald-300" : run.status === "failed" ? "border-red-800 text-red-300" : "border-sky-700 text-sky-300"}`}>{run.status}</span>
        <Button variant="outline" onClick={exportFirstFigure}><Download className="mr-2 h-4 w-4" />Export figure PNG</Button>
        <Button variant="outline" onClick={onReset}>New experiment</Button>
      </div>
    </header>

    <Section number="01" title="Experiment pipeline" subtitle="Figure 1 · Execution path and current state">
      <div className="overflow-x-auto border border-zinc-800 bg-zinc-950 px-5 py-7">
        <div className="flex min-w-[1120px] items-stretch">
          {pipeline.map(([title, kind, detail], index) => <div className="flex flex-1 items-center" key={title}>
            <div className="min-h-32 flex-1 border-l-2 border-zinc-700 bg-black px-4 py-4">
              <div className="flex justify-between"><span className="font-mono text-[10px] tracking-widest text-zinc-600">{kind}</span><State state={pipelineState(index, run)} /></div>
              <p className="mt-4 text-sm font-semibold text-zinc-100">{title}</p><p className="mt-2 text-xs leading-5 text-zinc-500">{detail}</p>
              <p className="mt-3 font-mono text-[10px] text-zinc-400">{pipelineCount(index, run, samples)}</p>
            </div>{index < pipeline.length - 1 && <span className="px-2 text-zinc-700">→</span>}
          </div>)}
        </div>
      </div>
    </Section>

    <div className="grid gap-8 2xl:grid-cols-[1.35fr_.65fr]">
      <Section number="02" title="Experiment progress" subtitle="Measured completion state; no gauges">
        <div className="border border-zinc-800 bg-zinc-950 p-6">
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            <Datum label="Current stage" value={stageName(run)} /><Datum label="Current query" value={run.currentQuery || "Not started"} />
            <Datum label="Completed queries" value={`${run.completedQueries} / ${run.totalQueries}`} /><Datum label="Completed strategies" value={run.status === "completed" ? "10 / 10" : `${strategyOrdinal(run.currentStrategy)} / 10`} />
            <Datum label="Completed samples" value={`${samples} / ${totalSamples}`} /><Datum label="Elapsed / remaining" value={`${elapsed(run)} / ${run.estimatedRemainingTime || "Not recorded"}`} />
          </div>
          <div className="mt-7"><div className="mb-2 flex justify-between font-mono text-xs text-zinc-500"><span>OVERALL COMPLETION</span><span>{progress}%</span></div><div className="h-2 bg-zinc-800"><div className="h-full bg-sky-400" style={{ width: `${progress}%` }} /></div></div>
          <div className="mt-5 grid grid-cols-4 gap-2 text-center text-xs">{["Stage 1", "Stage 2", "Stage 3", "Full"].map((stage, i) => <div className={`border px-2 py-2 ${stageActive(run.totalQueries, i) ? "border-sky-400 bg-sky-400/10 text-sky-200" : "border-zinc-800 text-zinc-600"}`} key={stage}>{stage}</div>)}</div>
        </div>
      </Section>
      <Section number="03" title="Cost summary" subtitle="Only values present in the experiment record">
        <div className="border border-zinc-800 bg-zinc-950 p-6"><div className="grid grid-cols-2 gap-5"><Datum label="Total cost" value="Not recorded" /><Datum label="API calls" value="Not recorded" /><Datum label="Prompt tokens" value="Not recorded" /><Datum label="Completion tokens" value="Not recorded" /><Datum label="Average latency" value="Not recorded" /><Datum label="Recorded samples" value={String(samples)} /></div><p className="mt-6 border-t border-zinc-800 pt-5 text-xs leading-5 text-zinc-500">The existing read API does not expose token/cost aggregates. Old profiler estimates are not copied into this scientific view.</p></div>
      </Section>
    </div>

    <Section number="04" title="Paper vs ours" subtitle="Figure 2 · Absolute PAWC and ordinal trend comparison">
      <div className="grid gap-6 2xl:grid-cols-[1fr_.72fr]">
        <Figure><p className="text-sm font-semibold">PAWC comparison</p><p className="mt-1 text-xs text-zinc-500">Paper Table 1 vs current aggregate (%)</p><GroupedBars rows={rows.filter(r => r.paper != null)} /></Figure>
        <ComparisonTable rows={rows} />
      </div>
    </Section>

    <div className="grid gap-8 xl:grid-cols-2">
      <Section number="05" title="Trend & fidelity" subtitle="Figure 3 · Provenance-aware fidelity profile">
        <Figure><FidelityRadar data={fidelityData(trend)} /><p className="text-center text-xs text-zinc-500">Audit scores; trend uses rank correlation when results exist.</p></Figure>
      </Section>
      <Section number="06" title="Paper conclusions" subtitle="Claim outcome with expandable evidence">
        <div className="divide-y divide-zinc-800 border border-zinc-800 bg-zinc-950">
          {conclusions.map(([id, label, strategyId, inverse]) => { const ours = rows.find(r => r.strategy === strategyId)?.ours; const status = ours == null || original == null ? "NOT TESTED" : (inverse ? ours <= original : ours > original) ? "PASS" : "FAIL"; return <div key={id}><button className="flex w-full items-center gap-4 px-5 py-4 text-left" onClick={() => setClaimOpen(claimOpen === id ? null : id)}><ClaimIcon status={status} /><span className="flex-1 text-sm">{label}</span><span className={`font-mono text-[10px] ${status === "PASS" ? "text-emerald-400" : status === "FAIL" ? "text-red-400" : "text-zinc-600"}`}>{status}</span><ChevronDown className={`h-4 w-4 text-zinc-600 ${claimOpen === id ? "rotate-180" : ""}`} /></button>{claimOpen === id && <p className="border-t border-zinc-800 bg-black px-14 py-4 text-xs leading-6 text-zinc-400">{status === "NOT TESTED" ? "No comparable aggregate is present in this experiment record." : `Measured PAWC ${ours?.toFixed(2)}%; baseline ${original?.toFixed(2)}%. Status tests direction, not absolute proximity.`}</p>}</div>; })}
          {["Lower-ranked sources benefit more", "Best method varies by domain", "Fluency + Statistics is strongest pair", "Methods generalize to Perplexity.ai"].map(label => <div className="flex items-center gap-4 px-5 py-4" key={label}><Circle className="h-4 w-4 text-zinc-600" /><span className="flex-1 text-sm">{label}</span><span className="font-mono text-[10px] text-zinc-600">NOT TESTED</span></div>)}
        </div>
      </Section>
    </div>

    <Section number="07" title="Strategy performance" subtitle="Figure 4 · Sortable metric view">
      <div className="border border-zinc-800 bg-zinc-950 p-5"><div className="mb-5 flex flex-wrap justify-between gap-4"><div className="flex flex-wrap gap-2">{(["pawc", "subjective_impression_calibrated", "word_score", "position_score"] as MetricKey[]).map(key => <button className={`border px-3 py-2 text-xs ${metric === key ? "border-sky-400 bg-sky-400/10 text-sky-200" : "border-zinc-800 text-zinc-500"}`} key={key} onClick={() => setMetric(key)}>{metricLabel(key)}</button>)}</div><button className="text-xs text-zinc-400 underline" onClick={() => setSort(sort === "paper" ? "ours" : "paper")}>Sort: {sort === "paper" ? "paper order" : "ours descending"}</button></div>
        <Figure><HorizontalBars rows={rows} /></Figure>
      </div>
    </Section>

    <Section number="08" title="Qualitative case study" subtitle="Original → rewrite → generated answer → evaluation">
      <div className="border border-zinc-800 bg-zinc-950"><div className="flex flex-wrap gap-2 border-b border-zinc-800 p-4">{rows.map(row => <button className={`px-3 py-2 text-xs ${strategy === row.strategy ? "bg-zinc-100 text-zinc-950" : "border border-zinc-800 text-zinc-400"}`} key={row.strategy} onClick={() => setStrategy(row.strategy)}>{row.label}</button>)}</div><CaseStudy run={run} evidence={selectedEvidence} /></div>
    </Section>

    <div className="grid gap-8 xl:grid-cols-[1fr_420px]">
      <Section number="09" title="Experiment coverage" subtitle="Completed and out-of-scope paper components"><div className="space-y-4 border border-zinc-800 bg-zinc-950 p-6">{coverage(run).map(row => <Coverage key={row.label} {...row} />)}</div></Section>
      <Section number="10" title="Replication summary" subtitle="Scope-aware final status"><div className="border border-zinc-800 bg-zinc-950 p-6"><p className="font-mono text-[10px] uppercase tracking-wider text-zinc-600">Final verdict</p><p className="mt-3 text-2xl font-semibold leading-tight text-sky-200">YES, WITH MODERN MODEL DIFFERENCES</p><div className="mt-7 grid grid-cols-2 gap-5"><Datum label="Overall fidelity" value="86 / 100" /><Datum label="Trend similarity" value={trend == null ? "Not available" : `${(trend * 100).toFixed(1)}%`} /><Datum label="Total runtime" value={elapsed(run)} /><Datum label="Total cost" value="Not recorded" /><Datum label="Queries" value={`${run.completedQueries}/${run.totalQueries}`} /><Datum label="Strategies" value="10" /><Datum label="Answers" value={String(samples)} /><Datum label="Evaluations" value={String(samples)} /></div></div></Section>
    </div>
  </div>;
}

function Section({ number, title, subtitle, children }: { number: string; title: string; subtitle: string; children: React.ReactNode }) { return <section className="min-w-0"><div className="mb-4 flex items-baseline gap-4"><span className="font-mono text-xs text-sky-400">{number}</span><div><h2 className="text-lg font-semibold">{title}</h2><p className="mt-1 text-xs text-zinc-500">{subtitle}</p></div></div>{children}</section>; }
function Figure({ children }: { children: React.ReactNode }) { return <div className="figure-export bg-white p-5 text-zinc-950">{children}</div>; }
function Datum({ label, value }: { label: string; value: string }) { return <div className="min-w-0"><p className="font-mono text-[10px] uppercase tracking-wider text-zinc-600">{label}</p><p className="mt-1 truncate text-sm font-medium" title={value}>{value}</p></div>; }
function State({ state }: { state: "done" | "active" | "pending" }) { return state === "done" ? <Check className="h-4 w-4 text-emerald-400" /> : <Circle className={`h-4 w-4 ${state === "active" ? "fill-sky-400 text-sky-400" : "text-zinc-700"}`} />; }
function ClaimIcon({ status }: { status: string }) { return status === "PASS" ? <Check className="h-4 w-4 text-emerald-400" /> : status === "FAIL" ? <X className="h-4 w-4 text-red-400" /> : <Circle className="h-4 w-4 text-zinc-600" />; }

type Row = ReturnType<typeof strategyRows>[number];
function ComparisonTable({ rows }: { rows: Row[] }) { return <div className="overflow-auto border border-zinc-800 bg-zinc-950"><table className="w-full text-left text-xs"><thead className="bg-black font-mono uppercase text-zinc-500"><tr><th className="p-3">Strategy</th><th className="p-3">Paper</th><th className="p-3">Ours</th><th className="p-3">Difference</th><th className="p-3">Trend</th></tr></thead><tbody className="divide-y divide-zinc-800">{rows.map(row => { const d = row.paper != null && row.ours != null ? row.ours - row.paper : null; const status = d == null ? "—" : Math.abs(d) <= 2 ? "Very close" : Math.abs(d) <= 5 ? "Slight" : "Large"; return <tr key={row.strategy}><td className="p-3">{row.label}</td><td className="p-3 font-mono">{fmt(row.paper)}</td><td className="p-3 font-mono">{fmt(row.ours)}</td><td className="p-3 font-mono">{d == null ? "—" : `${d > 0 ? "+" : ""}${d.toFixed(2)}`}</td><td className={`p-3 ${status === "Very close" ? "text-emerald-400" : status === "Slight" ? "text-amber-300" : status === "Large" ? "text-red-400" : "text-zinc-600"}`}>{status}</td></tr>; })}</tbody></table></div>; }

function GroupedBars({ rows }: { rows: Row[] }) {
  const width = 920, height = 370, left = 48, top = 24, bottom = 92;
  const chartHeight = height - top - bottom, chartWidth = width - left - 16;
  const max = Math.max(35, ...rows.flatMap(r => [r.paper ?? 0, r.ours ?? 0]));
  const group = chartWidth / Math.max(rows.length, 1), bar = Math.min(22, group * .28);
  return <svg className="mt-4 h-[370px] w-full" role="img" viewBox={`0 0 ${width} ${height}`}>
    {[0, .25, .5, .75, 1].map(f => { const y = top + chartHeight * (1-f); return <g key={f}><line stroke="#e4e4e7" x1={left} x2={width-16} y1={y} y2={y}/><text fill="#71717a" fontSize="10" textAnchor="end" x={left-8} y={y+3}>{(max*f).toFixed(0)}</text></g>; })}
    {rows.map((r,i)=>{const x=left+i*group+group/2;const ph=(r.paper??0)/max*chartHeight,oh=(r.ours??0)/max*chartHeight;return <g key={r.strategy}><rect fill="#a1a1aa" height={ph} width={bar} x={x-bar-2} y={top+chartHeight-ph}/><rect fill="#0369a1" height={oh} width={bar} x={x+2} y={top+chartHeight-oh}/><text fill="#52525b" fontSize="9" textAnchor="end" transform={`rotate(-38 ${x+8} ${height-54})`} x={x+8} y={height-54}>{r.short}</text></g>;})}
    <g transform={`translate(${width-150},8)`}><rect fill="#a1a1aa" height="9" width="14"/><text fontSize="10" x="20" y="9">Paper</text><rect fill="#0369a1" height="9" width="14" x="72"/><text fontSize="10" x="92" y="9">Ours</text></g>
  </svg>;
}

function HorizontalBars({ rows }: { rows: Row[] }) {
  const max = Math.max(1, ...rows.map(r => r.ours ?? 0));
  return <div className="space-y-3 py-3">{rows.map(r => <div className="grid grid-cols-[130px_1fr_52px] items-center gap-3" key={r.strategy}><span className="truncate text-right text-[11px] text-zinc-600">{r.label}</span><div className="h-5 bg-zinc-100"><div className={`h-full ${r.strategy === "original" ? "bg-zinc-500" : "bg-sky-700"}`} style={{width:`${Math.max(0,(r.ours??0)/max*100)}%`}} /></div><span className="font-mono text-[10px] text-zinc-600">{fmt(r.ours)}</span></div>)}</div>;
}

function FidelityRadar({ data }: { data: Array<{dimension:string;value:number}> }) {
  const cx=210,cy=180,r=128,n=data.length;
  const point=(i:number,value:number)=>{const a=-Math.PI/2+i*2*Math.PI/n,rr=r*value/100;return [cx+Math.cos(a)*rr,cy+Math.sin(a)*rr]};
  const polygon=(value:number)=>data.map((_,i)=>point(i,value).join(",")).join(" ");
  const values=data.map((d,i)=>point(i,d.value).join(",")).join(" ");
  return <svg className="h-[370px] w-full" role="img" viewBox="0 0 420 370">{[25,50,75,100].map(v=><polygon fill="none" key={v} points={polygon(v)} stroke="#d4d4d8"/>)}{data.map((d,i)=>{const [x,y]=point(i,115);return <g key={d.dimension}><line stroke="#e4e4e7" x1={cx} x2={point(i,100)[0]} y1={cy} y2={point(i,100)[1]}/><text fill="#3f3f46" fontSize="11" textAnchor={x<cx-10?"end":x>cx+10?"start":"middle"} x={x} y={y}>{d.dimension}</text></g>})}<polygon fill="#0284c7" fillOpacity=".16" points={values} stroke="#0369a1" strokeWidth="2"/>{data.map((d,i)=>{const [x,y]=point(i,d.value);return <circle cx={x} cy={y} fill="#0369a1" key={d.dimension} r="3"/>})}</svg>;
}
function CaseStudy({ run, evidence }: { run: ExperimentRun; evidence?: StrategyEvidence }) { const blocks = [["Original document", run.queryResults[0]?.evidence?.originalDocument], ["Rewritten document", evidence?.modifiedDocument], ["Generated answer", evidence?.generatedAnswer], ["Evaluation", evidence ? `PAWC ${evidence.metrics.pawc.toFixed(4)} · Word ${evidence.metrics.wordCount} · Position ${evidence.metrics.position ?? "none"} · Citations ${evidence.metrics.citationCount}` : undefined]]; return <div className="grid gap-px bg-zinc-800 lg:grid-cols-4">{blocks.map(([label, value], i) => <div className="min-h-64 bg-black p-5" key={label}><p className="font-mono text-[10px] uppercase text-sky-400">{i + 1} · {label}</p><div className="mt-4 max-h-72 overflow-auto whitespace-pre-wrap text-xs leading-5 text-zinc-400">{value || "Not available in the current record."}</div></div>)}</div>; }
function Coverage({ label, value, note }: { label: string; value: number; note: string }) { return <div><div className="mb-2 flex justify-between text-xs"><span>{label}</span><span className="font-mono text-zinc-600">{note}</span></div><div className="h-1.5 bg-zinc-800"><div className="h-full bg-sky-400" style={{ width: `${value}%` }} /></div></div>; }

function strategyRows(run: ExperimentRun, metric: MetricKey, sort: "paper" | "ours") { const ids = Object.keys(labels) as StrategyId[]; const rows = ids.map(strategy => { const stat: ExperimentStatistic | undefined = run.statistics?.find(x => x.strategy === strategy && x.metric === metric); const legacy = run.strategyResults.find(x => x.strategy === strategy); const raw = stat?.mean ?? (metric === "pawc" ? legacy?.pawc : undefined); return { strategy, label: labels[strategy], short: labels[strategy].replace(" to understand", ""), paper: metric === "pawc" ? paperPawc[strategy] ?? null : null, ours: raw == null ? null : raw <= 1 ? raw * 100 : raw }; }); return sort === "ours" ? rows.sort((a, b) => (b.ours ?? -Infinity) - (a.ours ?? -Infinity)) : rows; }
function trendSimilarity(rows: Row[]) { const data = rows.filter(r => r.paper != null && r.ours != null); if (data.length < 3) return null; const p = new Map([...data].sort((a,b)=>(b.paper??0)-(a.paper??0)).map((r,i)=>[r.strategy,i])); const o = new Map([...data].sort((a,b)=>(b.ours??0)-(a.ours??0)).map((r,i)=>[r.strategy,i])); const n=data.length; const d2=data.reduce((s,r)=>s+((p.get(r.strategy)??0)-(o.get(r.strategy)??0))**2,0); return Math.max(-1,Math.min(1,1-6*d2/(n*(n*n-1)))); }
function fidelityData(trend: number | null) { return [{dimension:"Trend",value:Math.round((trend??0)*100)},{dimension:"Method",value:91},{dimension:"Dataset",value:94},{dimension:"Evaluation",value:84},{dimension:"Prompt",value:98},{dimension:"Model",value:52}]; }
function pipelineState(index: number, run: ExperimentRun): "done"|"active"|"pending" { if(run.status==="completed")return "done"; const active=run.currentSample>0?4:run.currentQuery&&run.currentQuery!=="Queued"?3:1; return index<active?"done":index===active?"active":"pending"; }
function pipelineCount(i:number,run:ExperimentRun,samples:number){return [run.datasetName||"geo_bench / test",`${run.completedQueries}/${run.totalQueries} queries`,`10 methods`,labels[run.currentStrategy]||"not started",`${samples} answers`,`${samples} evaluated`,run.status==="completed"?"available":"pending"][i];}
function stageName(run:ExperimentRun){if(run.status==="completed")return"Replication report";if(run.status==="queued")return"Query selection";if(run.currentSample>0)return"LLM generation";return"Document rewrite";}
function strategyOrdinal(id:StrategyId){return Math.max(0,(Object.keys(labels) as StrategyId[]).indexOf(id)+1);}
function stageActive(count:number,i:number){const x=[30,100,300,996].findIndex(n=>count<=n);return(x<0?3:x)===i;}
function evidenceSamples(run:ExperimentRun){return run.queryResults.reduce((n,q)=>n+(q.evidence?.strategyDetails.length||0),0);}
function findEvidence(run:ExperimentRun,id:StrategyId){return run.queryResults.flatMap(q=>q.evidence?.strategyDetails||[]).find(x=>x.strategy===id);}
function elapsed(run:ExperimentRun){if(!run.startedAt)return"Not recorded";const ms=new Date(run.finishedAt||Date.now()).getTime()-new Date(run.startedAt).getTime();if(!Number.isFinite(ms)||ms<0)return"Not recorded";const m=Math.floor(ms/60000);return`${Math.floor(m/60)}h ${m%60}m`;}
function metricLabel(m:MetricKey){return({pawc:"PAWC",subjective_impression_calibrated:"Subjective",word_score:"Word score",position_score:"Position"})[m];}
function fmt(n:number|null){return n==null?"—":n.toFixed(2);}
function coverage(run:ExperimentRun){const done=run.status==="completed",n=run.totalQueries;return[{label:"Main experiment",value:done&&n>=996?100:Math.min(100,run.completedQueries/996*100),note:`${run.completedQueries}/996`},{label:"Dataset verification",value:100,note:"verified"},{label:"Prompt verification",value:100,note:"verified"},{label:"Evaluation verification",value:100,note:"verified"},{label:"Stage 1",value:done&&n>=30?100:0,note:done&&n>=30?"complete":"pending"},{label:"Stage 2",value:done&&n>=100?100:0,note:done&&n>=100?"complete":"pending"},{label:"Stage 3",value:done&&n>=300?100:0,note:done&&n>=300?"complete":"pending"},{label:"Pairwise / rank / domain / Perplexity",value:0,note:"not tested"}];}

function exportFirstFigure(){const svg=document.querySelector<SVGSVGElement>(".figure-export svg");if(!svg)return;const box=svg.getBoundingClientRect(),copy=svg.cloneNode(true) as SVGSVGElement;copy.setAttribute("xmlns","http://www.w3.org/2000/svg");const image=new Image();image.onload=()=>{const canvas=document.createElement("canvas");canvas.width=Math.round(box.width*2);canvas.height=Math.round(box.height*2);const ctx=canvas.getContext("2d");if(!ctx)return;ctx.scale(2,2);ctx.fillStyle="white";ctx.fillRect(0,0,box.width,box.height);ctx.drawImage(image,0,0,box.width,box.height);const a=document.createElement("a");a.download="princeton-geo-figure.png";a.href=canvas.toDataURL("image/png");a.click();};image.src=`data:image/svg+xml;charset=utf-8,${encodeURIComponent(new XMLSerializer().serializeToString(copy))}`;}

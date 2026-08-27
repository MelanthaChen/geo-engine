from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/geo-stage1-mpl")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
TOTAL_COST = 10.71  # Explicitly supplied with the figure specification.
PAPER_URL = "https://arxiv.org/html/2311.09735#S3"

COLORS = {
    "ink": "#172033",
    "muted": "#667085",
    "line": "#D0D5DD",
    "paper": "#98A2B3",
    "ours": "#175CD3",
    "accent": "#0E7490",
    "green": "#16803C",
    "red": "#C4320A",
    "gray": "#667085",
    "soft": "#F2F4F7",
    "yellow": "#B54708",
}

LABELS = {
    "original": "Original",
    "keyword_stuffing": "Keyword Stuffing",
    "unique_words": "Unique Words",
    "easy_to_understand": "Easy-to-Understand",
    "authoritative": "Authoritative",
    "technical_terms": "Technical Terms",
    "fluency": "Fluency",
    "citation": "Citation",
    "quotation": "Quotation",
    "statistics": "Statistics",
}

# Official paper Table 1, Position-Adjusted Word Count, Overall column.
PAPER_PAWC = {
    "original": 19.3,
    "keyword_stuffing": 17.7,
    "unique_words": 20.5,
    "easy_to_understand": 22.0,
    "authoritative": 21.3,
    "technical_terms": 22.7,
    "fluency": 24.7,
    "citation": 24.6,
    "quotation": 27.2,
    "statistics": 25.2,
}


def load_data():
    replication = json.loads((ROOT / "replication.json").read_text())
    verification = json.loads((ROOT / "paper_conclusion_verification.json").read_text())
    with (ROOT / "paper_objective_metrics.csv").open(newline="") as handle:
        objective = {row["strategy"]: row for row in csv.DictReader(handle)}
    with (ROOT / "paper_metrics.csv").open(newline="") as handle:
        metrics = list(csv.DictReader(handle))
    with (ROOT / "runs.csv").open(newline="") as handle:
        runs = list(csv.DictReader(handle))
    return replication, verification, objective, metrics, runs


R, V, O, M, RUNS = load_data()
OURS_PAWC = {key: float(row["pawc_mean"]) for key, row in O.items()}
START = datetime.fromisoformat(next(e["createdAt"] for e in R["timeline"] if e["type"] == "execution_started"))
END = datetime.fromisoformat(next(e["createdAt"] for e in R["timeline"] if e["type"] == "completed"))
RUNTIME_SECONDS = int((END - START).total_seconds())
RUNTIME_LABEL = f"{RUNTIME_SECONDS // 3600} h {(RUNTIME_SECONDS % 3600) // 60} m {RUNTIME_SECONDS % 60} s"


def setup():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 15,
        "axes.labelsize": 10,
        "axes.edgecolor": COLORS["line"],
        "axes.labelcolor": COLORS["ink"],
        "xtick.color": COLORS["muted"],
        "ytick.color": COLORS["muted"],
        "text.color": COLORS["ink"],
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "svg.fonttype": "none",
    })


def save(fig, stem):
    fig.savefig(OUT / f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def title(fig, text, subtitle=None):
    fig.text(.06, .955, text, fontsize=17, fontweight="bold", color=COLORS["ink"], va="top")
    if subtitle:
        fig.text(.06, .915, subtitle, fontsize=9, color=COLORS["muted"], va="top")


def figure1_workflow():
    fig, ax = plt.subplots(figsize=(9, 12))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    title(fig, "Stage 1 experiment workflow", "Princeton GEO replication · experiment 11")
    steps = [
        ("Official GEO-bench", "fixed test passages"),
        ("30 queries", "seeded Stage 1 subset"),
        ("10 GEO strategies", "baseline + nine methods"),
        ("Rewrite target passage", "one rewrite per query × strategy"),
        ("Generate 5 answers", "single n=5 completion batch"),
        ("Evaluation", "PAWC · Word · Position · Subjective × 7"),
        ("Trend verification", "paper claims and ranking concordance"),
        ("Replication report", "metrics · evidence · stage decision"),
    ]
    ys = np.linspace(.84, .17, len(steps))
    for i, ((heading, note), y) in enumerate(zip(steps, ys)):
        box = FancyBboxPatch((.19, y-.035), .62, .07, boxstyle="round,pad=.007,rounding_size=.008",
                             linewidth=1, edgecolor=COLORS["line"], facecolor="white")
        ax.add_patch(box)
        ax.text(.23, y+.009, heading, fontsize=12, fontweight="bold", va="center")
        ax.text(.77, y-.012, note, fontsize=8.5, color=COLORS["muted"], ha="right", va="center")
        if i < len(steps)-1:
            ax.annotate("", xy=(.5, ys[i+1]+.038), xytext=(.5, y-.038), arrowprops=dict(arrowstyle="-|>", color=COLORS["muted"], lw=1.2))
    summary = f"30 queries   ·   10 strategies   ·   5 answers per strategy   ·   1,500 generated answers\nRuntime {RUNTIME_LABEL}   ·   Total API cost ${TOTAL_COST:.2f}"
    ax.text(.5, .07, summary, ha="center", va="center", fontsize=9.5, color=COLORS["ink"],
            bbox=dict(boxstyle="round,pad=.6", facecolor=COLORS["soft"], edgecolor="none"))
    save(fig, "Figure01_Stage1_Workflow")


def figure2_paper_vs_stage1():
    order = list(PAPER_PAWC)
    x = np.arange(len(order)); width = .36
    fig, ax = plt.subplots(figsize=(13, 6.8))
    title(fig, "Paper vs Stage 1", "Position-Adjusted Word Count (PAWC), same 0–100 scale")
    fig.subplots_adjust(top=.82, bottom=.25, left=.08, right=.98)
    p = [PAPER_PAWC[s] for s in order]; o = [OURS_PAWC[s] for s in order]
    bars1 = ax.bar(x-width/2, p, width, color=COLORS["paper"], label="Princeton paper")
    bars2 = ax.bar(x+width/2, o, width, color=COLORS["ours"], label="Stage 1")
    ax.set_xticks(x, [LABELS[s] for s in order], rotation=32, ha="right")
    ax.set_ylabel("PAWC (%)"); ax.set_ylim(0, max(max(p), max(o))*1.22)
    ax.grid(axis="y", color=COLORS["line"], linewidth=.7, alpha=.7); ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, ncol=2, loc="upper left")
    highlights = {"quotation", "statistics", "citation", "fluency", "original"}
    for bars, values in ((bars1,p),(bars2,o)):
        for i,(bar,val) in enumerate(zip(bars,values)):
            ax.text(bar.get_x()+bar.get_width()/2, val+.35, f"{val:.1f}", ha="center", fontsize=8,
                    fontweight="bold" if order[i] in highlights else "normal")
    save(fig, "Figure02_Paper_vs_Stage1")


def figure3_ranking():
    paper_rank = sorted(PAPER_PAWC, key=PAPER_PAWC.get, reverse=True)
    ours_rank = sorted(OURS_PAWC, key=OURS_PAWC.get, reverse=True)
    lp = {s:i for i,s in enumerate(paper_rank)}; rp={s:i for i,s in enumerate(ours_rank)}
    fig, ax = plt.subplots(figsize=(10, 8.5)); ax.set_xlim(0,1); ax.set_ylim(9.7,-.7); ax.axis("off")
    title(fig, "Strategy ranking comparison", "Ranked by PAWC · lines reveal movement between the paper and Stage 1")
    fig.subplots_adjust(top=.84, left=.04, right=.96, bottom=.06)
    ax.text(.18,-.45,"PAPER RANKING",fontweight="bold",fontsize=10,ha="center",color=COLORS["muted"])
    ax.text(.82,-.45,"STAGE 1 RANKING",fontweight="bold",fontsize=10,ha="center",color=COLORS["muted"])
    for s in PAPER_PAWC:
        color = COLORS["red"] if s=="statistics" else (COLORS["ours"] if s in {"quotation","citation","fluency","original"} else COLORS["line"])
        lw = 3 if s=="statistics" else 1.3
        ax.plot([.31,.69],[lp[s],rp[s]],color=color,lw=lw,alpha=.85,zorder=1)
    for i,s in enumerate(paper_rank):
        ax.text(.29,i,f"{i+1}. {LABELS[s]}",ha="right",va="center",fontsize=10,fontweight="bold" if s=="statistics" else "normal")
    for i,s in enumerate(ours_rank):
        delta=lp[s]-i; arrow="↑" if delta>0 else "↓" if delta<0 else "—"
        ax.text(.71,i,f"{i+1}. {LABELS[s]}  {arrow}{abs(delta) if delta else ''}",ha="left",va="center",fontsize=10,
                color=COLORS["red"] if s=="statistics" else COLORS["ink"],fontweight="bold" if s=="statistics" else "normal")
    ax.text(.5,9.5,"Statistics moved from paper rank 2 to Stage 1 rank 8.",ha="center",fontsize=10,color=COLORS["red"],fontweight="bold")
    save(fig, "Figure03_Strategy_Ranking")


def figure4_claims():
    claims=V["claims"]
    fig, ax=plt.subplots(figsize=(12,10.5)); ax.set_xlim(0,1);ax.set_ylim(len(claims)+.5,-.8);ax.axis("off")
    title(fig,"PASS / FAIL summary","All claims from paper_conclusion_verification.json")
    fig.subplots_adjust(top=.87,left=.03,right=.97,bottom=.04)
    for i,c in enumerate(claims):
        status=c["status"]; color={"PASS":COLORS["green"],"FAIL":COLORS["red"],"NOT_TESTED":COLORS["gray"]}[status]
        if i%2==0: ax.add_patch(Rectangle((.02,i-.43),.96,.86,color=COLORS["soft"],zorder=0))
        ax.text(.045,i,"✓" if status=="PASS" else "✕" if status=="FAIL" else "○",color=color,fontsize=13,fontweight="bold",va="center")
        ax.text(.085,i,c["claim"],fontsize=9.1,va="center")
        ax.text(.955,i,status,color=color,fontsize=9,fontweight="bold",ha="right",va="center")
    save(fig,"Figure04_Claim_Summary")


def figure5_fidelity():
    f=V["fidelity"]
    names=["Dataset","Prompt","Method","Evaluation","Implementation","Model","Trend"]
    vals=[f["dataset_fidelity"]*100,0,f["method_fidelity"]*100,f["evaluation_fidelity"]*100,f["implementation_fidelity"]*100,0,f["trend_fidelity"]*100]
    n=len(names); angles=np.linspace(0,2*np.pi,n,endpoint=False).tolist(); vals2=vals+[vals[0]]; angles2=angles+[angles[0]]
    fig=plt.figure(figsize=(8.5,8.5)); ax=fig.add_subplot(111,polar=True);fig.subplots_adjust(top=.82,bottom=.08,left=.13,right=.87)
    title(fig,"Replication fidelity","Prompt and Model Fidelity are absent from the Stage 1 verification artifact and shown as unscored, not measured zero")
    ax.set_theta_offset(np.pi/2);ax.set_theta_direction(-1);ax.set_xticks(angles,names);ax.set_ylim(0,100);ax.set_yticks([20,40,60,80,100]);ax.set_yticklabels(["20","40","60","80","100"],fontsize=8,color=COLORS["muted"])
    ax.grid(color=COLORS["line"],lw=.7);ax.spines["polar"].set_color(COLORS["line"])
    ax.plot(angles2,vals2,color=COLORS["ours"],lw=2);ax.fill(angles2,vals2,color=COLORS["ours"],alpha=.14)
    for a,v in zip(angles,vals): ax.scatter([a],[v],s=25,color=COLORS["ours"])
    for index in (1, 5):
        ax.text(angles[index],8,"UNKNOWN",ha="center",va="center",fontsize=7,color=COLORS["red"],fontweight="bold")
    save(fig,"Figure05_Replication_Fidelity")


def figure6_stats():
    fig,ax=plt.subplots(figsize=(12,7.5));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis("off")
    title(fig,"Stage 1 statistics","Measured experiment scale, runtime, and supplied total API cost")
    answers=int(R["runCount"]); subjective=answers*7
    data=[("30","Queries"),("10","Strategies"),("5","Answers / strategy"),(f"{answers:,}","Generated answers"),(f"{subjective:,}","Subjective dimension scores"),(RUNTIME_LABEL,"Runtime"),(f"${TOTAL_COST:.2f}","Total API cost"),(f"${TOTAL_COST/30:.3f}","Average cost / query"),(f"${TOTAL_COST/10:.3f}","Average cost / strategy")]
    for i,(value,label) in enumerate(data):
        row,col=divmod(i,3); x=.055+col*.315;y=.77-row*.25
        ax.add_patch(FancyBboxPatch((x,y-.14),.285,.18,boxstyle="round,pad=.008",facecolor="white",edgecolor=COLORS["line"],lw=1))
        ax.text(x+.02,y-.025,value,fontsize=18 if len(value)<10 else 13,fontweight="bold",color=COLORS["ours"],va="center")
        ax.text(x+.02,y-.095,label,fontsize=9,color=COLORS["muted"],va="center")
    save(fig,"Figure06_Stage1_Statistics")


def figure7_cost():
    fig,ax=plt.subplots(figsize=(9,6.5));ax.axis("off");title(fig,"Cost breakdown","Data availability assessment for experiment 11")
    ax.add_patch(FancyBboxPatch((.12,.28),.76,.43,boxstyle="round,pad=.018",facecolor=COLORS["soft"],edgecolor=COLORS["line"],transform=ax.transAxes))
    ax.text(.5,.61,f"Total API cost: ${TOTAL_COST:.2f}",ha="center",transform=ax.transAxes,fontsize=18,fontweight="bold",color=COLORS["ours"])
    ax.text(.5,.48,"Category percentages cannot be calculated from the saved run.",ha="center",transform=ax.transAxes,fontsize=12,fontweight="bold")
    ax.text(.5,.39,"runs.csv contains blank input_tokens, output_tokens, total_tokens, and token_cost fields.\nNo Answer / Rewrite / Subjective cost totals are present in replication.json.",ha="center",transform=ax.transAxes,fontsize=9.5,color=COLORS["muted"],linespacing=1.6)
    ax.text(.5,.18,"No pie chart is drawn because assigning shares would invent values.",ha="center",transform=ax.transAxes,fontsize=10,color=COLORS["red"])
    save(fig,"Figure07_Cost_Breakdown_Data_Gap")


def figure8_trend():
    f=V["fidelity"]; trend=f["trend_fidelity"]*100; decision=V["stage_decision"]
    fig,ax=plt.subplots(figsize=(10,8));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis("off");title(fig,"Trend similarity","Stage 1 decision summary")
    ax.text(.5,.70,f"{trend:.1f}%",ha="center",va="center",fontsize=64,fontweight="bold",color=COLORS["red"])
    ax.text(.5,.59,"TREND SIMILARITY",ha="center",fontsize=10,color=COLORS["muted"],fontweight="bold")
    items=[("Method",f["method_fidelity"]),("Implementation",f["implementation_fidelity"]),("Dataset",f["dataset_fidelity"]),("Evaluation",f["evaluation_fidelity"]),("Model",None)]
    for i,(name,val) in enumerate(items):
        x=.12+i*.19; ax.text(x,.43,name,ha="center",fontsize=8,color=COLORS["muted"]);ax.text(x,.38,"UNKNOWN" if val is None else f"{val*100:.1f}%",ha="center",fontsize=12,fontweight="bold")
    ax.add_patch(FancyBboxPatch((.29,.16),.42,.12,boxstyle="round,pad=.01",facecolor="#FEF3F2",edgecolor="#FDA29B"))
    ax.text(.5,.235,decision["decision"],ha="center",fontsize=20,fontweight="bold",color=COLORS["red"])
    ax.text(.5,.185,f"Trend similarity below {decision['threshold']*100:.0f}% threshold",ha="center",fontsize=9,color=COLORS["muted"])
    save(fig,"Figure08_Trend_Similarity")


def figure9_findings():
    fig,ax=plt.subplots(figsize=(12,7.5));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis("off");title(fig,"Scientific findings","Directional reproduction of Princeton GEO Stage 1 claims")
    ax.add_patch(FancyBboxPatch((.05,.32),.42,.48,boxstyle="round,pad=.012",facecolor="#ECFDF3",edgecolor="#ABEFC6"))
    ax.add_patch(FancyBboxPatch((.53,.32),.42,.48,boxstyle="round,pad=.012",facecolor="#FEF3F2",edgecolor="#FECDCA"))
    ax.text(.09,.74,"SUCCESSFULLY REPLICATED",fontsize=10,fontweight="bold",color=COLORS["green"])
    ax.text(.57,.74,"NOT REPLICATED",fontsize=10,fontweight="bold",color=COLORS["red"])
    for i,s in enumerate(["Quotation","Citation","Fluency","Authoritative","Keyword Stuffing"]): ax.text(.10,.66-i*.07,f"✓  {s}",fontsize=12,color=COLORS["ink"])
    for i,s in enumerate(["Statistics","Easy-to-Understand"]): ax.text(.58,.66-i*.09,f"✕  {s}",fontsize=12,color=COLORS["ink"])
    ax.text(.5,.20,"MAIN OBSERVATION",ha="center",fontsize=9,fontweight="bold",color=COLORS["muted"])
    ax.text(.5,.12,"Modern GPT models reproduced most tested Princeton GEO directions,\nbut Statistics Addition did not improve visibility in Stage 1.",ha="center",fontsize=13,fontweight="bold",linespacing=1.5)
    save(fig,"Figure09_Scientific_Findings")


def figure10_future():
    fig,ax=plt.subplots(figsize=(10,9));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis("off");title(fig,"Replication roadmap","Completed work and experiments gated by the Stage 1 decision")
    items=[("Methodology Audit",True),("Scientific Provenance Audit",True),("Stage 1 Replication",True),("Statistics Failure Analysis",False),("Stage 2",False),("Stage 3",False),("Full Benchmark",False),("Pairwise Experiment",False),("Rank Analysis",False),("Domain Analysis",False),("Perplexity Experiment",False)]
    ys=np.linspace(.82,.13,len(items))
    ax.plot([.17,.17],[ys[-1],ys[0]],color=COLORS["line"],lw=2)
    for (label,done),y in zip(items,ys):
        color=COLORS["green"] if done else COLORS["gray"]
        ax.scatter([.17],[y],s=125,facecolor="white",edgecolor=color,lw=2,zorder=3)
        ax.text(.17,y,"✓" if done else "",ha="center",va="center",color=color,fontweight="bold",fontsize=9)
        ax.text(.23,y,label,va="center",fontsize=11,fontweight="bold" if done or label=="Statistics Failure Analysis" else "normal",color=COLORS["ink"] if done else COLORS["muted"])
        ax.text(.82,y,"COMPLETE" if done else "PENDING",ha="right",va="center",fontsize=8,fontweight="bold",color=color)
    save(fig,"Figure10_Future_Work")


def main():
    setup()
    for function in [figure1_workflow,figure2_paper_vs_stage1,figure3_ranking,figure4_claims,figure5_fidelity,figure6_stats,figure7_cost,figure8_trend,figure9_findings,figure10_future]:
        function()
    print(f"Generated 20 figure files in {OUT}")


if __name__ == "__main__":
    main()

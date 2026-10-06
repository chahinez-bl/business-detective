import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { Banner, CreateAction, InsightBody, InsightCard, NeedData, PageHead, Sev } from "../../components/ui"
import { Bars } from "../../components/charts"
import { money } from "../../lib/format"
import { useWs } from "../../state/workspace"

export function Insights() {
  const [area, setArea] = useState("All"); const [sev, setSev] = useState("All")
  return <NeedData>{d => {
    const areas = ["All", ...Array.from(new Set(d.insights.map(i => i.area)))]
    const list = d.insights.filter(i => (area === "All" || i.area === area) && (sev === "All" || i.severity === sev))
    return <><PageHead title="Insights" sub="What changed, why it matters and what to do — most important first." />
      <div className="row mb" role="group" aria-label="Filter by area">{areas.map(a => <button key={a} className={"chip" + (area === a ? " on" : "")} onClick={() => setArea(a)}>{a}</button>)}
        <span className="mute">|</span>{["All", "Critical", "High", "Medium", "Low"].map(s => <button key={s} className={"chip" + (sev === s ? " on" : "")} onClick={() => setSev(s)}>{s}</button>)}</div>
      {list.length ? <div className="col">{list.map(i => <InsightCard key={i.id} i={i} />)}</div> : <Banner kind="ok">No findings match this filter.</Banner>}</>
  }}</NeedData>
}

export function InsightDetail() {
  const { id } = useParams(); const { base } = useWs()
  return <NeedData>{d => {
    const i = d.insights.find(x => String(x.id) === id)
    if (!i) return <Banner kind="err">We couldn't find this insight. <Link to={`${base}/insights`}>Back to insights</Link></Banner>
    const contrib = i.details?.contributors as { name: string; delta: number }[] | undefined
    return <><Link to={`${base}/insights`} className="row sm b mb"><ArrowLeft size={16} /> All insights</Link>
      <div className="row between"><div className="row">{i.category === "Opportunity" ? <span className="badge opp">Opportunity</span> : <Sev s={i.severity} />}<span className="mute sm">{i.area}</span></div><CreateAction insight={i} /></div>
      <h1 style={{ marginTop: 10 }}>{i.title}</h1>
      <div className="grid g2"><InsightBody i={i} cur={d.currency} />
        <div className="col">{contrib && contrib.length > 0 && <div className="card"><h3>What's driving the change?</h3><p className="sm mute">Change in revenue by {d.root_cause?.dimension ?? "item"}. These show where the change is concentrated; they are possible contributing factors, not proven causes.</p>
          <Bars data={contrib} x="name" y="delta" horizontal height={220} fmt={v => money(v, d.currency)} color="#c4560a" /></div>}
          {i.details?.factors?.length > 0 && <div className="card"><h3>Possible contributing factors</h3><ul style={{ margin: 0, paddingLeft: 18 }}>{i.details.factors.map((f: string, k: number) => <li key={k}>{f}</li>)}</ul></div>}</div></div></>
  }}</NeedData>
}

export function Recommendations() {
  return <NeedData>{d => <><PageHead title="Recommendations" sub="Suggested actions, each tied to evidence from your data." />
    {d.recommendations.length === 0 ? <Banner kind="ok">No recommendations right now — nothing needs action.</Banner> : <div className="col">{d.recommendations.map(r => {
      const ins = d.insights.find(i => i.id === r.insight_id)!
      return <div key={r.id} className="card"><div className="row between"><div className="row"><Sev s={r.priority} /><span className="xs mute">{r.area} · confidence {Math.round(r.confidence * 100)}%</span></div>{ins && <CreateAction insight={ins} recId={r.id} label="Turn into action" />}</div>
        <h3 style={{ marginTop: 8 }}>{r.title}</h3>
        <div className="grid g3 sm"><div className="sect"><h4>Problem</h4>{r.problem}</div><div className="sect"><h4>Evidence</h4>{r.evidence}</div><div className="sect" style={{ background: "#f1f8f4" }}><h4>Recommended action</h4>{r.action}</div></div>
        <p className="sm mute" style={{ margin: "8px 0 0" }}>Objective: {r.objective} · Impact: {ins?.impact_text}</p></div>
    })}</div>}</>}</NeedData>
}

export function DecisionCenter() {
  return <NeedData>{d => {
    const g = d.decision.groups
    let n = 0
    return <><PageHead title="Decision Center" sub="What should I do today?" />
      {d.decision.count === 0 ? <Banner kind="ok">No priorities today: nothing high or medium priority was detected.</Banner> :
        (["Critical", "High", "Medium"] as const).map(s => g[s]?.length ? <section key={s} className="mb"><h2 className="row"><Sev s={s} /> {s === "Critical" ? "Do first" : s === "High" ? "Do soon" : "Plan"}</h2>
          <div className="col">{g[s].map(i => { n += 1; return <div key={i.id} className={`alert ${i.severity}`}>
            <div className="row between"><b>{n}. {i.title}</b><CreateAction insight={i} /></div>
            <div className="grid g2 sm mt"><div><div className="xs mute b">PROBLEM</div>{i.what}</div><div><div className="xs mute b">IMPACT</div>{i.impact_text}</div>
              <div><div className="xs mute b">EVIDENCE</div>{i.evidence.slice(0, 2).join("; ")}</div><div><div className="xs mute b">RECOMMENDED ACTION</div>{i.action}</div></div>
            <p className="xs mute" style={{ margin: "8px 0 0" }}>Confidence {Math.round(i.confidence * 100)}% · {i.area}</p></div> })}</div></section> : null)}
      {d.decision.opportunities.length > 0 && <><h2 className="mt2">Worth seizing</h2><div className="col">{d.decision.opportunities.map(i => <InsightCard key={i.id} i={i} compact />)}</div></>}</>
  }}</NeedData>
}

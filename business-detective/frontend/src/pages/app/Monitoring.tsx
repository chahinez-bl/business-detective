import { useState } from "react"
import { Link } from "react-router-dom"
import { Banner, CreateAction, InsightBody, NeedData, Sev, Status } from "../../components/ui"
import { RevenueChart } from "../../components/charts"
import { dateLabel } from "../../lib/format"
import { useWs } from "../../state/workspace"

export default function Monitoring() {
  const { base } = useWs()
  const [open, setOpen] = useState<number | null>(null)
  return <NeedData>{d => {
    const m = d.monitoring
    const marks = d.insights.filter(i => i.kind === "anomaly" && i.detected_on && i.category === "Anomaly").map(i => i.detected_on!)
    return <>
      <div className="pagehead row between"><div><h1>Business monitor</h1><p>Is your business okay, and what needs your attention?</p></div></div>
      <div className="card row" style={{ gap: 28 }}>
        <div><div className="mute sm b">Overall status</div><div className="mt"><Status s={m.status} /></div></div>
        <div><div className="mute sm b">Business health</div><div className="score">{m.health.overall ?? "—"}<span className="mute" style={{ fontSize: "1rem" }}>{m.health.overall != null ? " / 100" : ""}</span></div></div>
        <div><div className="mute sm b">Active alerts</div><div className="score">{m.total_alerts}</div></div>
        {m.health.overall == null && <p className="sm mute" style={{ margin: 0 }}>Not enough data to calculate this metric.</p>}
      </div>
      <h2 className="mt2">By area</h2>
      <div className="grid g4">{m.areas.map(a => <div className="tile" key={a.area}><div className="row between"><span className="nm">{a.area}</span><Status s={a.status} /></div>
        <p className="sm mute" style={{ margin: "8px 0 0" }}>{a.monitored ? a.message : "Not available with this data"}</p></div>)}</div>
      {m.areas.some(a => !a.monitored) && <details className="mt"><summary>Why are some areas not monitored?</summary><ul className="sm mute">{m.areas.filter(a => !a.monitored).map(a => <li key={a.area}><b>{a.area}:</b> {a.message}</li>)}</ul></details>}
      <h2 className="mt2">Active alerts</h2>
      {m.alerts.length === 0 ? <Banner kind="ok">No active alerts. Nothing unusual detected in the data you provided.</Banner> :
        <div className="col">{m.alerts.map(i => <div key={i.id} className={`alert ${i.severity}`}>
          <div className="row between"><div className="row"><Sev s={i.severity} /><span className="xs mute">{i.area} · {dateLabel(i.detected_on)}</span></div><CreateAction insight={i} /></div>
          <h3 style={{ margin: "8px 0 4px", fontSize: "1.02rem" }}>{i.title}</h3><p className="sm" style={{ margin: 0 }}>{i.what}</p>
          <button className="btn ghost sm" style={{ paddingLeft: 0 }} onClick={() => setOpen(open === i.id ? null : i.id)}>{open === i.id ? "Hide details" : "Why it matters, evidence and what to do"}</button>
          {open === i.id && <div className="mt"><InsightBody i={i} cur={d.currency} /></div>}</div>)}
          {m.total_alerts > m.alerts.length && <Link to={`${base}/insights`} className="b sm">See all {m.total_alerts} findings →</Link>}</div>}
      <div className="grid g2 mt2">
        <div><h2>Trend</h2><div className="card"><RevenueChart data={d.daily} cur={d.currency} marks={marks} height={230} />{marks.length > 0 && <p className="xs mute" style={{ margin: "6px 0 0" }}>Dotted lines mark unusual days.</p>}</div></div>
        <div><h2>Recent events</h2><div className="card">{m.recent_events.length ? m.recent_events.map(e => <div key={e.id} className="row" style={{ padding: "6px 0", borderBottom: "1px solid var(--line)" }}><span className="xs mute" style={{ width: 90 }}>{dateLabel(e.detected_on)}</span><Link to={`${base}/insights/${e.id}`} className="sm">{e.title}</Link></div>) : <p className="mute sm">No events yet.</p>}</div></div></div>
      {m.opportunities.length > 0 && <><h2 className="mt2">Opportunities</h2><div className="grid g2">{m.opportunities.map(i => <div key={i.id} className="alert Opportunity"><span className="badge opp">Opportunity</span><h3 style={{ margin: "8px 0 4px", fontSize: "1rem" }}>{i.title}</h3><p className="sm" style={{ margin: 0 }}>{i.what}</p></div>)}</div></>}
    </>
  }}</NeedData>
}

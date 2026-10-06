import { Link } from "react-router-dom"
import { Check, Circle } from "lucide-react"
import { Banner, Change, InsightCard, NeedData, Stat, Status } from "../../components/ui"
import { RevenueChart } from "../../components/charts"
import { dateLabel, greeting, moneyShort, num } from "../../lib/format"
import { useAuth } from "../../state/auth"
import { useWs } from "../../state/workspace"

export default function Overview() {
  const { user } = useAuth(); const { mode, base, data, loading, readOnly } = useWs()
  const first = (user?.name || "").split(" ")[0]
  if (!loading && data && !data.has_data && mode === "customer") return <>
    <div className="pagehead"><h1>Welcome{first ? `, ${first}` : ""} 👋</h1><p>Your workspace “{data.business.name}” is ready. Let's bring in your data.</p></div>
    <div className="card"><h3>Getting started</h3>
      {[["Tell us about your business", true], ["Upload your data (CSV or Excel)", false], ["We inspect it and show a data-quality check", false], ["Confirm the detected columns", false], ["Analyze your business", false], ["Your monitoring dashboard is ready", false]].map(([t, done], k) =>
        <div className="row" key={k} style={{ padding: "7px 0" }}>{done ? <Check size={18} color="#177a4b" /> : <Circle size={18} color="#9db0b7" />}<span className={done ? "mute" : ""}>{t as string}</span></div>)}
      {!readOnly ? <Link className="btn mt" to={`${base}/import`}>Upload your data</Link> : <p className="mute">Ask a workspace admin to upload data.</p>}
      <p className="sm mute mt">Want to see it first? <Link to="/demo">Explore the demo</Link> (fictional data).</p></div></>
  return <NeedData>{d => {
    const k = d.kpis, p = k.period, cur = d.currency
    return <>
      <div className="pagehead"><h1>{greeting()}{first && mode === "customer" ? `, ${first}` : ""} 👋</h1><p>Here's what needs your attention.</p></div>
      <div className="grid g4 mb">
        <div className="card"><div className="lbl mute b sm">Business health</div>{d.health.overall != null ? <><div className="score">{d.health.overall}<span className="mute" style={{ fontSize: "1rem" }}> / 100</span></div><div className="mt"><Status s={d.monitoring.status} /></div></> : <p className="sm mute">Not enough data to calculate this metric.</p>}</div>
        <Stat label={p ? `Revenue · last ${p.days} days` : "Total revenue"} value={moneyShort(p ? p.revenue : k.revenue, cur)} sub={p ? <><Change v={p.revenue_change_pct} /> vs previous {p.days} days</> : `${k.days} days of data`} />
        {p?.profit != null ? <Stat label={`Gross profit · last ${p.days} days`} value={moneyShort(p.profit, cur)} sub={p.profit_change_pct != null ? <><Change v={p.profit_change_pct} /> vs previous</> : undefined} /> : d.profitability ? <Stat label="Gross profit" value={moneyShort(d.profitability.profit, cur)} sub={`Margin ${d.profitability.margin_pct?.toFixed(1)}%`} /> : null}
        {k.orders != null && <Stat label={p?.orders != null ? `Orders · last ${p.days} days` : "Orders"} value={num(p?.orders ?? k.orders)} sub={p?.orders_change_pct != null ? <><Change v={p.orders_change_pct} /> vs previous</> : undefined} />}
      </div>
      <h2>Needs attention</h2>
      {d.overview.attention.length ? <div className="col">{d.overview.attention.map(i => <InsightCard key={i.id} i={i} />)}
        <Link to={`${base}/monitoring`} className="b sm">Open the full monitor →</Link></div>
        : <Banner kind="ok">Nothing unusual was detected in your data. We keep checking every time you add new data.</Banner>}
      {d.overview.opportunities.length > 0 && <><h2 className="mt2">Opportunities</h2><div className="col">{d.overview.opportunities.map(i => <InsightCard key={i.id} i={i} compact />)}</div></>}
      <h2 className="mt2">Revenue</h2><div className="card"><RevenueChart data={d.daily} cur={cur} /></div>
      <div className="card flat mt2"><div className="row between"><div><b>About this analysis</b><p className="sm mute" style={{ margin: 0 }}>{d.dataset?.filename} · {dateLabel(k.start)} → {dateLabel(k.end)} · {num(d.quality?.rows_accepted)} rows used{d.quality?.rows_rejected ? `, ${num(d.quality.rows_rejected)} rejected` : ""} · data quality {d.quality?.score}/100</p></div>
        {mode === "customer" && <Link className="btn sec sm" to={`${base}/datasets`}>View data</Link>}</div>
        {Object.values(d.capabilities).some(c => !c.available) && <details style={{ marginTop: 10 }}><summary>What we can't analyze with this data</summary>
          <ul className="sm mute">{Object.values(d.capabilities).filter(c => !c.available).map(c => <li key={c.label}><b>{c.label}:</b> {c.reason}</li>)}</ul></details>}</div>
    </>
  }}</NeedData>
}

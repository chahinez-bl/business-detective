import { useState } from "react"
import { api } from "../../api/client"
import { Banner, NeedData, PageHead, Needs, Spinner } from "../../components/ui"
import { money, num, pct } from "../../lib/format"
import { useWs } from "../../state/workspace"

export const WhatIf = () => <Needs cap="products">{d => <Sim products={d.products.filter(p => p.units)} cur={d.currency} />}</Needs>

function Sim({ products, cur }: { products: any[]; cur: string }) {
  const { mode, bid } = useWs()
  const [product, setProduct] = useState(""); const [price, setPrice] = useState("5"); const [cost, setCost] = useState("0"); const [vol, setVol] = useState("0"); const [el, setEl] = useState(""); const [res, setRes] = useState<any>(null); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false)
  const run = async () => {
    setBusy(true); setErr("")
    try { setRes(await api.post(mode === "demo" ? "/demo/simulate" : `/businesses/${bid}/simulate`, { product: product || null, price_pct: Number(price) || 0, cost_pct: Number(cost) || 0, volume_pct: Number(vol) || 0, elasticity: el === "" ? null : Number(el) })) }
    catch (e: any) { setErr(e.message); setRes(null) }
    setBusy(false)
  }
  return <><PageHead title="What-if simulator" sub="Try a change and see an estimate of the effect over 30 days." />
    <Banner kind="warn"><b>Simulation — not actual results.</b> The starting point is your real average sales; the outcome is an estimate based on the changes you enter.</Banner>
    <div className="card mt"><div className="grid g3">
      <label className="f">Applies to<select value={product} onChange={e => setProduct(e.target.value)}><option value="">All products</option>{products.map(p => <option key={p.product}>{p.product}</option>)}</select></label>
      <label className="f">Change selling price (%)<input type="number" value={price} onChange={e => setPrice(e.target.value)} /></label>
      <label className="f">Change purchase cost (%)<input type="number" value={cost} onChange={e => setCost(e.target.value)} /></label>
      <label className="f">Change sales volume (%)<input type="number" value={vol} onChange={e => setVol(e.target.value)} /></label>
      <label className="f">Price elasticity <small>optional assumption, e.g. -1.2</small><input type="number" step="0.1" value={el} placeholder="not assumed" onChange={e => setEl(e.target.value)} /></label></div>
      <p className="sm mute">Without an elasticity, a price change does not change volume. If you enter one, volume also moves by elasticity × price change — your assumption, not something we measured.</p>
      <button className="btn" onClick={run} disabled={busy}>{busy ? <Spinner /> : "Run simulation"}</button>{err && <div className="mt"><Banner kind="err">{err}</Banner></div>}</div>
    {res && <div className="card mt"><div className="row between"><h3 style={{ margin: 0 }}>{res.scope}</h3><span className="badge sev-Medium">{res.label}</span></div>
      <div className="tw mt"><table><thead><tr><th>30 days</th><th>Current (from your data)</th><th>Simulated</th><th>Difference</th></tr></thead><tbody>{res.rows.map((r: any) => { const u = r.metric.startsWith("Units"); return <tr key={r.metric}><td>{r.metric}</td><td>{u ? num(r.current) : money(r.current, cur)}</td><td>{u ? num(r.simulated) : money(r.simulated, cur)}</td><td className={r.delta >= 0 ? "up b" : "down b"}>{u ? num(r.delta) : money(r.delta, cur)}</td></tr> })}
        {res.margin && <tr><td>Margin</td><td>{pct(res.margin.current)}</td><td>{pct(res.margin.simulated)}</td><td /></tr>}</tbody></table></div>
      {res.note && <p className="sm mute">{res.note}</p>}</div>}</>
}

export function Assistant() {
  const { mode, bid } = useWs()
  const [log, setLog] = useState<{ q: string; a: string }[]>([]); const [q, setQ] = useState(""); const [busy, setBusy] = useState(false)
  const go = async (t: string) => {
    if (t.trim().length < 2) return
    setBusy(true); let a: string
    try { a = (await api.post(mode === "demo" ? "/demo/ask" : `/businesses/${bid}/ask`, { question: t })).answer } catch (e: any) { a = e.message }
    setLog(l => [...l, { q: t, a }]); setQ(""); setBusy(false)
  }
  const S = ["Why did my sales change?", "What's unusual?", "What should I prioritize?", "Which products are performing badly?", "Which products may run out of stock?", "Which products hurt my profit?"]
  return <NeedData>{() => <><PageHead title="Business analyst" sub="Ask a question. Answers come only from your analysis — nothing is made up." />
    <div className="row mb">{S.map(s => <button key={s} className="chip" onClick={() => go(s)}>{s}</button>)}</div>
    <div className="chat">{log.map((m, k) => <div key={k}><div className="m me">{m.q}</div><div className="m">{m.a}</div></div>)}{busy && <Spinner />}</div>
    <div className="row mt"><input style={{ flex: 1, minWidth: 200 }} value={q} placeholder="Ask about your business…" onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === "Enter" && go(q)} aria-label="Your question" /><button className="btn" disabled={busy} onClick={() => go(q)}>Ask</button></div>
    <p className="xs mute mt">If something can't be answered reliably from your data, the analyst says so.</p></>}</NeedData>
}

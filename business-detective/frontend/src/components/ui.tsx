import { CSSProperties, ReactNode, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { AlertTriangle, CheckCircle2, ChevronRight, Info, Lock, X } from "lucide-react"
import { api } from "../api/client"
import type { Insight } from "../api/types"
import { money, pct } from "../lib/format"
import { useWs } from "../state/workspace"

export const Logo = ({ light = false }: { light?: boolean }) => (
  <span className="logo" style={light ? { color: "#fff" } : undefined}>
    <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden><rect width="32" height="32" rx="8" fill={light ? "#1b5a6b" : "#0f4c5c"} /><circle cx="14" cy="14" r="6.5" fill="none" stroke="#fff" strokeWidth="2.6" /><path d="M19 19l6 6" stroke="#f2b134" strokeWidth="3" strokeLinecap="round" /></svg>
    Business Detective
  </span>
)

export const Sev = ({ s }: { s: string }) => <span className={`badge sev-${s}`}>{s}</span>
export const Status = ({ s }: { s: string | null }) => <span className={`badge ${s ? "st-" + s : "st-na"}`}><span className="dot" style={{ background: "currentColor", width: 8, height: 8 }} />{s ?? "Not monitored"}</span>
export const Spinner = () => <span className="spinner" role="status" aria-label="Loading" />
export const Loading = ({ text = "Loading…" }: { text?: string }) => <div className="empty"><Spinner /><p className="mute">{text}</p></div>

export function Banner({ kind = "info", children }: { kind?: "info" | "warn" | "err" | "ok" | "demo"; children: ReactNode }) {
  const I = kind === "ok" ? CheckCircle2 : kind === "info" || kind === "demo" ? Info : AlertTriangle
  return <div className={`banner ${kind}`} role={kind === "err" ? "alert" : undefined}><I size={18} style={{ flex: "none", marginTop: 2 }} /><div>{children}</div></div>
}

export const PageHead = ({ title, sub, children }: { title: string; sub?: string; children?: ReactNode }) => (
  <div className="pagehead row between"><div><h1>{title}</h1>{sub && <p>{sub}</p>}</div>{children && <div className="row">{children}</div>}</div>
)

export const Stat = ({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: "up" | "down" }) => (
  <div className="card stat"><div className="lbl">{label}</div><div className="val">{value}</div>{sub && <div className={`sm ${tone ?? "mute"}`}>{sub}</div>}</div>
)

export const Change = ({ v }: { v: number | null | undefined }) => v == null ? null : <span className={v >= 0 ? "up" : "down"}>{v >= 0 ? "▲" : "▼"} {pct(Math.abs(v))}</span>

export const Unavailable = ({ reason, title }: { reason: string; title?: string }) => (
  <div className="card empty"><Lock size={28} color="#7b8a92" /><h3 style={{ marginTop: 8 }}>{title ?? "This analysis isn't available"}</h3><p style={{ maxWidth: 520, margin: "0 auto" }}>{reason}</p></div>
)

/** Wraps a page that needs an analysed dataset. */
export function NeedData({ children }: { children: (d: NonNullable<ReturnType<typeof useWs>["data"]>) => ReactNode }) {
  const { data, loading, error, base, mode } = useWs()
  if (loading && !data) return <Loading />
  if (error) return <Banner kind="err">{error}</Banner>
  if (!data || !data.has_data) return (
    <div className="card empty"><h3>No analysis yet</h3><p>Upload your business data and we'll show what's happening, what needs attention and what to do next.</p>
      {mode === "customer" && <Link className="btn" to={`${base}/import`}>Upload your data</Link>}</div>)
  return <>{children(data)}</>
}

/** Capability gate: shows an honest explanation instead of an empty or fabricated page. */
export function Needs({ cap, children }: { cap: string; children: (d: NonNullable<ReturnType<typeof useWs>["data"]>) => ReactNode }) {
  return <NeedData>{d => d.capabilities[cap]?.available ? children(d) : <Unavailable reason={d.capabilities[cap]?.reason ?? "This analysis is unavailable because your dataset does not contain the required information."} />}</NeedData>
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => { const h = (e: KeyboardEvent) => e.key === "Escape" && onClose(); window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h) }, [onClose])
  return <div className="modal" onMouseDown={e => e.target === e.currentTarget && onClose()}><div className="card" role="dialog" aria-modal="true" aria-label={title}>
    <div className="row between mb"><h3 style={{ margin: 0 }}>{title}</h3><button className="btn ghost sm" onClick={onClose} aria-label="Close"><X size={16} /></button></div>{children}</div></div>
}

export function CreateAction({ insight, recId, label = "Create action" }: { insight: Insight | null; recId?: number | null; label?: string }) {
  const { bid, reload, readOnly } = useWs()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState(""); const [note, setNote] = useState(""); const [due, setDue] = useState(""); const [who, setWho] = useState("")
  const [members, setMembers] = useState<any[]>([]); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false)
  if (readOnly) return null
  if (insight?.action_item) return <Link className="badge st-Attention" to="/app/actions">Action: {insight.action_item.status.replace("_", " ")} →</Link>
  const show = async () => {
    setTitle((insight?.action ?? "").slice(0, 120)); setErr(""); setOpen(true)
    try { setMembers(await api.get(`/businesses/${bid}/members`)) } catch { /* optional */ }
  }
  const save = async () => {
    setBusy(true); setErr("")
    try {
      await api.post(`/businesses/${bid}/actions`, { title, note, insight_id: insight?.id ?? null, recommendation_id: recId ?? insight?.recommendation_id ?? null, assignee_id: who ? Number(who) : null, due_date: due || null })
      setOpen(false); await reload()
    } catch (e: any) { setErr(e.message) }
    setBusy(false)
  }
  return <>
    <button className="btn sec sm" onClick={show}>{label}</button>
    {open && <Modal title="Create an action" onClose={() => setOpen(false)}><div className="col">
      {insight && <p className="sm mute" style={{ margin: 0 }}>From: {insight.title}</p>}
      <label className="f">What needs to be done?<input value={title} onChange={e => setTitle(e.target.value)} maxLength={200} autoFocus /></label>
      <div className="grid g2"><label className="f">Assign to<select value={who} onChange={e => setWho(e.target.value)}><option value="">Nobody yet</option>{members.map(m => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select></label>
        <label className="f">Due date<input type="date" value={due} onChange={e => setDue(e.target.value)} /></label></div>
      <label className="f">Note <small>(optional)</small><textarea rows={3} value={note} onChange={e => setNote(e.target.value)} /></label>
      {err && <Banner kind="err">{err}</Banner>}
      <div className="row"><button className="btn" disabled={!title.trim() || busy} onClick={save}>Save action</button><button className="btn ghost" onClick={() => setOpen(false)}>Cancel</button></div>
    </div></Modal>}
  </>
}

export function InsightCard({ i, compact = false }: { i: Insight; compact?: boolean }) {
  const { base } = useWs()
  return <div className={`alert ${i.category === "Opportunity" ? "Opportunity" : i.severity}`}>
    <div className="row between"><div className="row">{i.category === "Opportunity" ? <span className="badge opp">Opportunity</span> : <Sev s={i.severity} />}<span className="xs mute">{i.area}</span></div>
      <CreateAction insight={i} /></div>
    <h3 style={{ margin: "8px 0 4px", fontSize: "1.02rem" }}><Link to={`${base}/insights/${i.id}`} style={{ color: "inherit" }}>{i.title}</Link></h3>
    <p className="sm" style={{ margin: 0 }}>{i.what}</p>
    {!compact && <p className="sm mute" style={{ margin: "6px 0 0" }}>{i.impact_text}</p>}
    <div style={{ marginTop: 6 }}><Link to={`${base}/insights/${i.id}`} className="sm b">See details <ChevronRight size={14} style={{ verticalAlign: -2 }} /></Link></div>
  </div>
}

/** WHAT / WHY / IMPACT / EVIDENCE / ACTION, with the technical detail tucked under "Details". */
export function InsightBody({ i, cur }: { i: Insight; cur: string }) {
  const d = i.details || {}
  return <div className="col">
    <div className="sect"><h4>What happened</h4>{i.what}</div>
    <div className="sect"><h4>Why it matters</h4>{i.why}</div>
    <div className="sect"><h4>Impact</h4>{i.impact_text}</div>
    <div className="sect"><h4>Evidence</h4><ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>{i.evidence.map((e, k) => <li key={k}>{e}</li>)}</ul></div>
    <div className="sect" style={{ background: "#f1f8f4", borderColor: "#cfe8d8" }}><h4>What to do</h4>{i.action}</div>
    <details><summary>Details and how this was calculated</summary>
      <div className="sm mute" style={{ marginTop: 8 }}>
        <p>{d.method}</p>
        {d.metric && <p>Metric: {d.metric}{d.observed != null && <> · observed {Number(d.observed).toLocaleString("en-US", { maximumFractionDigits: 1 })}</>}{d.baseline != null && <> · baseline {Number(d.baseline).toLocaleString("en-US", { maximumFractionDigits: 1 })}</>}{d.deviation != null && <> · change {pct(d.deviation, true)}</>}</p>}
        <p>Confidence {Math.round(i.confidence * 100)}% · detected {i.detected_on ?? "—"} · currency {cur}. Estimates come from your own historical data, not guarantees.</p>
      </div></details>
  </div>
}

export const MoneyText = ({ v, cur, style }: { v: number | null | undefined; cur: string; style?: CSSProperties }) => <span style={style}>{money(v, cur)}</span>

import { DragEvent, useCallback, useEffect, useRef, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { AlertTriangle, CheckCircle2, FileSpreadsheet, Info, XCircle } from "lucide-react"
import { api } from "../../api/client"
import { Banner, Loading, PageHead, Spinner } from "../../components/ui"
import { dateLabel, num } from "../../lib/format"
import { useWs } from "../../state/workspace"

const STEPS = ["Upload", "Preview", "Detected columns", "Confirm columns", "Data quality", "Analyze"]
const REQUIRED = new Set(["date", "revenue", "quantity", "price"])

export function Import() {
  const { bid, reload, readOnly } = useWs(); const nav = useNavigate()
  const [step, setStep] = useState(0); const [file, setFile] = useState<File | null>(null); const [pctUp, setPctUp] = useState(0); const [busy, setBusy] = useState(false); const [err, setErr] = useState("")
  const [up, setUp] = useState<any>(null); const [map, setMap] = useState<Record<string, string>>({}); const [q, setQ] = useState<any>(null); const [over, setOver] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  if (readOnly) return <Banner kind="warn">Your role in this workspace is read-only, so you can't upload data.</Banner>

  const pick = async (f: File | undefined) => {
    if (!f) return
    setFile(f); setErr(""); setBusy(true); setPctUp(0)
    try { const r = await api.upload(`/businesses/${bid}/datasets/upload`, f, setPctUp); setUp(r); setMap(r.suggested_mapping); setStep(1) }
    catch (e: any) { setErr(e.message); setFile(null) }
    setBusy(false)
  }
  const drop = (e: DragEvent) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files?.[0]) }
  const clean = () => Object.fromEntries(Object.entries(map).filter(([, v]) => v))
  const validate = async () => {
    setBusy(true); setErr("")
    try { setQ(await api.post(`/businesses/${bid}/datasets/${up.dataset.id}/validate`, { mapping: clean() })); setStep(4) } catch (e: any) { setErr(e.message) }
    setBusy(false)
  }
  const analyze = async () => {
    setBusy(true); setErr(""); setStep(5)
    try { await api.post(`/businesses/${bid}/datasets/${up.dataset.id}/analyze`, { mapping: clean() }); await reload(); nav("/app/monitoring") }
    catch (e: any) { setErr(e.message); if (e.extra?.quality) setQ(e.extra.quality); setStep(4) }
    setBusy(false)
  }
  const fields: { key: string; label: string; help: string }[] = up?.fields ?? []
  const hasAmount = !!map.revenue || (!!map.quantity && !!map.price)
  const canGo = !!map.date && hasAmount

  return <><PageHead title="Import your data" sub="Upload a CSV or Excel file. We'll check it with you before analyzing anything." />
    <div className="steps" aria-label="Progress">{STEPS.map((s, k) => <div key={s} className={k === step ? "on" : k < step ? "done" : ""}>{k + 1}. {s}</div>)}</div>
    {err && <div className="mb"><Banner kind="err">{err}</Banner></div>}

    {step === 0 && <div className="card"><div className={"drop" + (over ? " over" : "")} onDragOver={e => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)} onDrop={drop} onClick={() => input.current?.click()} role="button" tabIndex={0} onKeyDown={e => e.key === "Enter" && input.current?.click()}>
      <FileSpreadsheet size={40} color="#0f4c5c" /><h3 style={{ marginTop: 10 }}>Drag your file here, or click to choose</h3><p className="mute">CSV or Excel (.xlsx) · up to 15 MB · English or French column names</p>
      {busy && <div style={{ maxWidth: 320, margin: "14px auto 0" }}><div className="bar"><i style={{ width: pctUp + "%" }} /></div><p className="sm mute">Uploading {file?.name}… {pctUp}%</p></div>}
      <input ref={input} type="file" hidden accept=".csv,.xlsx" onChange={e => pick(e.target.files?.[0])} /></div>
      <details className="mt"><summary>What should my file contain?</summary><p className="sm mute">One row per sale (or order line). At minimum a <b>date</b> and a <b>sales amount</b> — or a quantity and a unit price. Optional columns unlock more analyses: product, stock level, purchase cost, supplier, customer, returns. You don't need to rename columns.</p></details></div>}

    {step === 1 && up && <div className="card"><h3>{up.dataset.filename} <span className="mute sm">· {num(up.total_rows)} rows · {up.columns.length} columns{up.sheet ? ` · sheet “${up.sheet}”` : ""}</span></h3>
      <div className="tw"><table><thead><tr>{up.columns.map((c: string) => <th key={c}>{c}</th>)}</tr></thead><tbody>{up.preview.slice(0, 6).map((r: any, k: number) => <tr key={k}>{up.columns.map((c: string) => <td key={c}>{String(r[c] ?? "")}</td>)}</tr>)}</tbody></table></div>
      <p className="sm mute">First rows of your file. Does it look right?</p><div className="row"><button className="btn" onClick={() => setStep(2)}>Looks right — continue</button><button className="btn ghost" onClick={() => { setStep(0); setUp(null) }}>Choose another file</button></div></div>}

    {step === 2 && up && <div className="card"><h3>Here's what we detected</h3>
      {Object.keys(map).length === 0 ? <Banner kind="warn">We couldn't recognise any columns automatically. You can choose them yourself in the next step.</Banner> :
        <div className="col">{fields.filter(f => map[f.key]).map(f => <div className="row" key={f.key}><CheckCircle2 size={18} color="#177a4b" /><b style={{ minWidth: 190 }}>{f.label}</b><span className="mute">←</span><code>{map[f.key]}</code></div>)}</div>}
      {!canGo && <div className="mt"><Banner kind="warn">We still need {!map.date ? "a date column" : ""}{!map.date && !hasAmount ? " and " : ""}{!hasAmount ? "a revenue column (or quantity and unit price)" : ""}. You can pick them next.</Banner></div>}
      <div className="row mt"><button className="btn" onClick={() => setStep(3)}>Review and confirm</button><button className="btn ghost" onClick={() => setStep(1)}>Back</button></div></div>}

    {step === 3 && up && <div className="card"><h3>Confirm the columns</h3><p className="sm mute">Change anything that's wrong. Optional fields can be left empty — you only get the analyses your data supports.</p>
      <div className="grid g2">{fields.map(f => <label className="f" key={f.key}>{f.label}{REQUIRED.has(f.key) ? <small>{f.key === "date" ? "Required" : "Required (revenue, or quantity + unit price)"}</small> : <small>Optional</small>}
        <select value={map[f.key] ?? ""} onChange={e => setMap({ ...map, [f.key]: e.target.value })}><option value="">— not in my file —</option>{up.columns.map((c: string) => <option key={c} value={c}>{c}</option>)}</select><small>{f.help}</small></label>)}</div>
      {!canGo && <div className="mt"><Banner kind="warn">Choose a date column and a revenue column (or both quantity and unit price) to continue.</Banner></div>}
      <div className="row mt"><button className="btn" disabled={!canGo || busy} onClick={validate}>{busy ? <Spinner /> : "Check my data"}</button><button className="btn ghost" onClick={() => setStep(2)}>Back</button></div></div>}

    {step === 4 && q && <Quality q={q} busy={busy} onBack={() => setStep(3)} onGo={analyze} />}

    {step === 5 && <div className="card center empty"><Spinner /><h3 style={{ marginTop: 12 }}>Analyzing your business…</h3><p className="mute">Studying trends, unusual days, products, stock, margins and customers. This usually takes a few seconds.</p></div>}
  </>
}

function Quality({ q, busy, onBack, onGo }: { q: any; busy: boolean; onBack: () => void; onGo: () => void }) {
  const tone = q.score >= 85 ? "#177a4b" : q.score >= 60 ? "#a16207" : "#b42318"
  const I = { error: XCircle, warning: AlertTriangle, info: Info } as const
  return <div className="col">
    <div className="card row" style={{ gap: 28 }}><div><div className="mute sm b">Data quality</div><div className="score" style={{ color: tone }}>{q.score}<span className="mute" style={{ fontSize: "1rem" }}> / 100</span></div></div>
      <div className="grid g4" style={{ flex: 1 }}>{[["Rows received", q.rows_received], ["Rows accepted", q.rows_accepted], ["Rows rejected", q.rows_rejected], ["Duplicates removed", q.duplicates_removed]].map(([l, v]) => <div key={l as string}><div className="mute xs b">{l}</div><div className="b" style={{ fontSize: "1.4rem" }}>{num(v as number)}</div></div>)}</div></div>
    {q.date_range && <p className="sm mute" style={{ margin: 0 }}>Period covered: {dateLabel(q.date_range.start)} → {dateLabel(q.date_range.end)} ({q.date_range.days} days)</p>}
    <div className="card"><h3>Checks passed</h3>{q.passed.map((p: string) => <div className="row sm" key={p}><CheckCircle2 size={16} color="#177a4b" />{p}</div>)}</div>
    {q.issues.length > 0 && <div className="card"><h3>Things to know</h3><div className="col">{q.issues.map((i: any, k: number) => { const Icon = I[i.severity as keyof typeof I]; return <div key={k} className="row" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}><Icon size={18} color={i.severity === "error" ? "#b42318" : i.severity === "warning" ? "#a16207" : "#1d5fa6"} style={{ flex: "none", marginTop: 3 }} />
      <div><b>{i.message}</b>{i.consequence && <div className="sm mute">{i.consequence}</div>}{i.fix && <div className="sm">How to fix: {i.fix}</div>}</div></div> })}</div></div>}
    {q.can_analyze && <div className="card"><h3>What you'll get</h3><div className="grid g2">{Object.values(q.capabilities).map((c: any) => <div key={c.label} className="row sm" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>{c.available ? <CheckCircle2 size={16} color="#177a4b" style={{ flex: "none", marginTop: 3 }} /> : <XCircle size={16} color="#9db0b7" style={{ flex: "none", marginTop: 3 }} />}<div><b>{c.label}</b>{!c.available && <div className="mute">{c.reason}</div>}</div></div>)}</div></div>}
    <div className="row">{q.can_analyze ? <button className="btn lg" disabled={busy} onClick={onGo}>Analyze my business</button> : <Banner kind="err">We can't analyze this yet. Fix the issues above or adjust the column mapping.</Banner>}<button className="btn ghost" onClick={onBack}>Change columns</button></div></div>
}

export function Datasets() {
  const { bid, base, readOnly, reload } = useWs(); const [rows, setRows] = useState<any[] | null>(null); const [err, setErr] = useState("")
  const load = useCallback(async () => { try { setRows(await api.get(`/businesses/${bid}/datasets`)) } catch (e: any) { setErr(e.message) } }, [bid])
  useEffect(() => { load() }, [load])
  const del = async (id: number) => { if (!confirm("Delete this dataset and everything computed from it (insights, recommendations, reports)? This cannot be undone.")) return; try { await api.del(`/businesses/${bid}/datasets/${id}`); await load(); await reload() } catch (e: any) { setErr(e.message) } }
  return <><PageHead title="My data" sub="Every file you've uploaded. The latest analysis drives your dashboard.">{!readOnly && <Link className="btn" to={`${base}/import`}>Upload new data</Link>}</PageHead>
    {err && <Banner kind="err">{err}</Banner>}{!rows ? <Loading /> : rows.length === 0 ? <div className="card empty"><h3>No data yet</h3><p>Upload a CSV or Excel file to begin.</p></div> :
      <div className="card pad0 tw"><table><thead><tr><th>File</th><th>Uploaded</th><th>Rows</th><th>Quality</th><th>Status</th><th /></tr></thead><tbody>{rows.map(r => <tr key={r.id}><td className="b">{r.filename}</td><td>{dateLabel(r.created_at)}</td><td>{num(r.row_count)}</td><td>{r.quality_score ?? "—"}</td>
        <td><span className={"badge " + (r.status === "analyzed" ? "st-Normal" : r.status === "failed" ? "st-Critical" : "st-na")}>{r.status}</span></td><td>{!readOnly && <button className="btn danger sm" onClick={() => del(r.id)}>Delete</button>}</td></tr>)}</tbody></table></div>}</>
}

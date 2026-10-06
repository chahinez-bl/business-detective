import { FormEvent, useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { api } from "../../api/client"
import { Banner, Loading, PageHead, Spinner } from "../../components/ui"
import { dateLabel } from "../../lib/format"
import { useAuth } from "../../state/auth"
import { useWs } from "../../state/workspace"

const CURRENCIES: [string, string][] = [["DZD", "DZD — Algerian dinar"], ["EUR", "EUR — Euro"], ["USD", "USD — US dollar"], ["GBP", "GBP — Pound sterling"], ["MAD", "MAD — Moroccan dirham"], ["TND", "TND — Tunisian dinar"], ["CAD", "CAD — Canadian dollar"], ["CHF", "CHF — Swiss franc"], ["AED", "AED — UAE dirham"], ["SAR", "SAR — Saudi riyal"]]
const INDUSTRIES = ["Retail", "Food & beverage", "Wholesale / distribution", "E-commerce", "Manufacturing", "Services", "Other"]

export function Onboarding() {
  const { refresh } = useAuth(); const { setBid } = useWs(); const nav = useNavigate()
  const [name, setName] = useState(""); const [industry, setIndustry] = useState("Retail"); const [cur, setCur] = useState("DZD"); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false)
  const go = async (e: FormEvent) => { e.preventDefault(); setBusy(true); setErr("")
    try { const b = await api.post("/businesses", { name, industry, currency: cur }); setBid(b.id); await refresh(); nav("/app/import", { replace: true }) } catch (x: any) { setErr(x.message) } setBusy(false) }
  return <div style={{ maxWidth: 560, margin: "30px auto" }}><div className="steps"><div className="on">1. Your business</div><div>2. Upload data</div><div>3. Inspect</div><div>4. Confirm columns</div><div>5. Analyze</div><div>6. Dashboard</div></div>
    <div className="card"><h2>Welcome to Business Detective</h2><p className="mute">Tell us about your business.</p><form className="col" onSubmit={go}>
      <label className="f">Business name<input required value={name} maxLength={120} placeholder="My Retail Store" onChange={e => setName(e.target.value)} autoFocus /></label>
      <label className="f">Industry<select value={industry} onChange={e => setIndustry(e.target.value)}>{INDUSTRIES.map(i => <option key={i}>{i}</option>)}</select></label>
      <label className="f">Currency<small>Used to show every amount. You can change it later.</small><select value={cur} onChange={e => setCur(e.target.value)}>{CURRENCIES.map(([c, l]) => <option key={c} value={c}>{l}</option>)}</select></label>
      {err && <Banner kind="err">{err}</Banner>}<button className="btn" disabled={busy || !name.trim()}>{busy ? <Spinner /> : "Create my workspace"}</button></form></div></div>
}

export function Reports() {
  const { bid, readOnly, data } = useWs(); const [rows, setRows] = useState<any[] | null>(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState("")
  const load = useCallback(async () => { try { setRows(await api.get(`/businesses/${bid}/reports`)) } catch (e: any) { setErr(e.message) } }, [bid])
  useEffect(() => { load() }, [load])
  const make = async () => { setBusy(true); setErr(""); try { const r = await api.post(`/businesses/${bid}/reports`); await load(); await api.download(`/businesses/${bid}/reports/${r.id}/download`, `business-report-${r.id}.pdf`) } catch (e: any) { setErr(e.message) } setBusy(false) }
  const del = async (id: number) => { if (confirm("Delete this report?")) { await api.del(`/businesses/${bid}/reports/${id}`); load() } }
  return <><PageHead title="Reports" sub="Professional PDF reports built from your own data: health, alerts, evidence, impact, recommendations and actions.">{!readOnly && <button className="btn" onClick={make} disabled={busy || !data?.has_data}>{busy ? <Spinner /> : "Generate PDF report"}</button>}</PageHead>
    {!data?.has_data && <Banner kind="info">Upload and analyze your data first, then you can generate a report.</Banner>}{err && <Banner kind="err">{err}</Banner>}
    {!rows ? <Loading /> : rows.length > 0 && <div className="card pad0 tw mt"><table><thead><tr><th>Report</th><th>Created</th><th>Size</th><th /></tr></thead><tbody>{rows.map(r => <tr key={r.id}><td className="b">{r.title}</td><td>{dateLabel(r.created_at)}</td><td>{Math.round(r.size_bytes / 1024)} KB</td>
      <td className="row"><button className="btn sec sm" onClick={() => api.download(`/businesses/${bid}/reports/${r.id}/download`, `business-report-${r.id}.pdf`).catch(e => setErr(e.message))}>Download</button>{!readOnly && <button className="btn danger sm" onClick={() => del(r.id)}>Delete</button>}</td></tr>)}</tbody></table></div>}</>
}

export function Settings() {
  const { user, businesses, refresh, logout } = useAuth(); const { bid, data, reload } = useWs(); const nav = useNavigate()
  const biz = businesses.find(b => b.id === bid); const admin = biz?.role === "owner" || biz?.role === "admin"
  const [name, setName] = useState(user?.name ?? ""); const [msg, setMsg] = useState(""); const [err, setErr] = useState("")
  const [bn, setBn] = useState(biz?.name ?? ""); const [bi, setBi] = useState(biz?.industry ?? ""); const [bc, setBc] = useState(biz?.currency ?? "DZD")
  const [cp, setCp] = useState(""); const [np, setNp] = useState(""); const [members, setMembers] = useState<any[]>([]); const [em, setEm] = useState(""); const [role, setRole] = useState("member"); const [busy, setBusy] = useState(false)
  const loadMembers = useCallback(async () => { if (bid) try { setMembers(await api.get(`/businesses/${bid}/members`)) } catch { /* ignore */ } }, [bid])
  useEffect(() => { loadMembers() }, [loadMembers])
  const run = async (fn: () => Promise<any>, ok: string) => { setMsg(""); setErr(""); try { await fn(); setMsg(ok) } catch (e: any) { setErr(e.message) } }
  const rerun = async () => { setBusy(true); try { const ds = await api.get(`/businesses/${bid}/datasets/${data!.dataset!.id}`); await api.post(`/businesses/${bid}/datasets/${ds.id}/analyze`, { mapping: ds.mapping }); await reload(); setMsg("Analysis updated.") } catch (e: any) { setErr(e.message) } setBusy(false) }
  if (!biz) return <Loading />
  return <><PageHead title="Settings" />{msg && <div className="mb"><Banner kind="ok">{msg}</Banner></div>}{err && <div className="mb"><Banner kind="err">{err}</Banner></div>}
    <div className="grid g2"><div className="card col"><h3>Your account</h3>
      <label className="f">Name<input value={name} onChange={e => setName(e.target.value)} /></label><label className="f">Email<input value={user?.email} disabled /></label>
      <button className="btn sec" onClick={() => run(async () => { await api.patch("/auth/me", { name }); await refresh() }, "Profile saved.")}>Save</button>
      <hr style={{ border: 0, borderTop: "1px solid var(--line)", width: "100%" }} /><h4 style={{ margin: 0 }}>Change password</h4>
      <input type="password" placeholder="Current password" value={cp} onChange={e => setCp(e.target.value)} autoComplete="current-password" /><input type="password" placeholder="New password (8+ characters, letters and numbers)" value={np} onChange={e => setNp(e.target.value)} autoComplete="new-password" />
      <button className="btn sec" disabled={!cp || !np} onClick={() => run(async () => { await api.post("/auth/password", { current_password: cp, new_password: np }); setCp(""); setNp("") }, "Password changed.")}>Change password</button>
      <button className="btn ghost" onClick={async () => { await logout(); nav("/") }}>Sign out</button></div>
    <div className="card col"><h3>Business</h3><label className="f">Business name<input value={bn} onChange={e => setBn(e.target.value)} disabled={!admin} /></label>
      <label className="f">Industry<input value={bi} onChange={e => setBi(e.target.value)} disabled={!admin} /></label>
      <label className="f">Currency<select value={bc} onChange={e => setBc(e.target.value)} disabled={!admin}>{CURRENCIES.map(([c, l]) => <option key={c} value={c}>{l}</option>)}</select></label>
      {admin ? <button className="btn" onClick={() => run(async () => { await api.patch(`/businesses/${bid}`, { name: bn, industry: bi, currency: bc }); await refresh(); await reload() }, "Business updated. If you changed the currency, re-run the analysis below.")}>Save business</button> : <p className="sm mute">Only owners and admins can change these settings.</p>}
      {admin && data?.has_data && <button className="btn sec" disabled={busy} onClick={rerun}>{busy ? <Spinner /> : "Re-run analysis with current settings"}</button>}</div></div>
    <div className="card mt"><h3>Team</h3><div className="tw"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th></tr></thead><tbody>{members.map(m => <tr key={m.user_id}><td>{m.name}</td><td>{m.email}</td><td>{m.role}</td></tr>)}</tbody></table></div>
      {admin && <div className="row mt"><input style={{ flex: 1, minWidth: 200 }} type="email" placeholder="Teammate's email (they must have an account)" value={em} onChange={e => setEm(e.target.value)} /><select style={{ width: 130 }} value={role} onChange={e => setRole(e.target.value)}><option value="admin">Admin</option><option value="member">Member</option><option value="viewer">Viewer</option></select>
        <button className="btn sec" disabled={!em} onClick={() => run(async () => { await api.post(`/businesses/${bid}/members`, { email: em, role }); setEm(""); await loadMembers() }, "Teammate added.")}>Add</button></div>}
      <p className="xs mute">Viewers can read everything but cannot upload data, create actions or generate reports.</p></div>
    {biz.role === "owner" && <div className="card mt"><h3>Danger zone</h3><p className="sm mute">Deleting this business permanently removes its data, uploaded files, insights, actions and reports.</p>
      <button className="btn danger" onClick={async () => { if (confirm(`Permanently delete “${biz.name}” and all of its data?`)) { try { await api.del(`/businesses/${bid}`); await refresh(); nav("/app", { replace: true }) } catch (e: any) { setErr((e as Error).message) } } }}>Delete this business</button></div>}</>
}

import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../../api/client"
import type { ActionItem } from "../../api/types"
import { Banner, Loading, Modal, PageHead } from "../../components/ui"
import { dateLabel } from "../../lib/format"
import { useWs } from "../../state/workspace"

const COLS: [ActionItem["status"], string][] = [["todo", "To do"], ["in_progress", "In progress"], ["resolved", "Resolved"]]

export default function Actions() {
  const { bid, readOnly, base, reload } = useWs()
  const [items, setItems] = useState<ActionItem[] | null>(null); const [members, setMembers] = useState<any[]>([]); const [err, setErr] = useState("")
  const [edit, setEdit] = useState<ActionItem | null>(null); const [showArch, setShowArch] = useState(false); const [creating, setCreating] = useState(false)
  const load = useCallback(async () => {
    try { setItems(await api.get(`/businesses/${bid}/actions`)); setMembers(await api.get(`/businesses/${bid}/members`)) } catch (e: any) { setErr(e.message) }
  }, [bid])
  useEffect(() => { load() }, [load])
  const patch = async (id: number, body: any) => { try { await api.patch(`/businesses/${bid}/actions/${id}`, body); await load(); reload() } catch (e: any) { setErr(e.message) } }
  if (!items) return err ? <Banner kind="err">{err}</Banner> : <Loading />
  const card = (a: ActionItem) => <div className="act" key={a.id}>
    <div className="b">{a.title}</div>
    {a.source_title && <div className="xs mute">From: {a.source_title}</div>}
    <div className="row xs mute" style={{ margin: "6px 0" }}>{a.assignee && <span>👤 {a.assignee}</span>}{a.due_date && <span className={a.overdue ? "down b" : ""}>📅 {dateLabel(a.due_date)}{a.overdue ? " (overdue)" : ""}</span>}</div>
    {a.note && <p className="sm mute" style={{ margin: "4px 0" }}>{a.note}</p>}
    {!readOnly && <div className="row">
      {a.status === "todo" && <button className="btn sec sm" onClick={() => patch(a.id, { status: "in_progress" })}>Start</button>}
      {a.status === "in_progress" && <><button className="btn sm" onClick={() => patch(a.id, { status: "resolved" })}>Mark resolved</button><button className="btn ghost sm" onClick={() => patch(a.id, { status: "todo" })}>Back to To do</button></>}
      {a.status === "resolved" && <button className="btn ghost sm" onClick={() => patch(a.id, { status: "todo" })}>Reopen</button>}
      {a.status === "dismissed" && <button className="btn ghost sm" onClick={() => patch(a.id, { status: "todo" })}>Restore</button>}
      <button className="btn ghost sm" onClick={() => setEdit(a)}>Edit</button>
      {a.status !== "dismissed" && <button className="btn ghost sm" onClick={() => patch(a.id, { status: "dismissed" })}>Archive</button>}</div>}
  </div>
  return <><PageHead title="Actions" sub="Turn what you've learned into things that get done.">{!readOnly && <button className="btn" onClick={() => setCreating(true)}>New action</button>}</PageHead>
    {err && <div className="mb"><Banner kind="err">{err}</Banner></div>}
    {items.filter(a => a.status !== "dismissed").length === 0 && <div className="card empty"><h3>No actions yet</h3><p>Create one from any alert or recommendation — or <Link to={`${base}/decision-center`}>see today's priorities</Link>.</p></div>}
    <div className="kan">{COLS.map(([s, l]) => <div key={s}><div className="colh">{l} <span className="mute">({items.filter(a => a.status === s).length})</span></div>{items.filter(a => a.status === s).map(card)}</div>)}</div>
    {items.some(a => a.status === "dismissed") && <div className="mt2"><button className="btn ghost sm" onClick={() => setShowArch(!showArch)}>{showArch ? "Hide" : "Show"} archived ({items.filter(a => a.status === "dismissed").length})</button>{showArch && items.filter(a => a.status === "dismissed").map(card)}</div>}
    {(edit || creating) && <ActionForm key={edit?.id ?? "new"} item={edit} members={members} onClose={() => { setEdit(null); setCreating(false) }} onSave={async b => {
      if (edit) await patch(edit.id, b); else { try { await api.post(`/businesses/${bid}/actions`, b); await load(); reload() } catch (e: any) { setErr(e.message) } }
      setEdit(null); setCreating(false) }} />}</>
}

function ActionForm({ item, members, onClose, onSave }: { item: ActionItem | null; members: any[]; onClose: () => void; onSave: (b: any) => Promise<void> }) {
  const [title, setTitle] = useState(item?.title ?? ""); const [note, setNote] = useState(item?.note ?? ""); const [who, setWho] = useState(String(item?.assignee_id ?? "")); const [due, setDue] = useState(item?.due_date ?? "")
  return <Modal title={item ? "Edit action" : "New action"} onClose={onClose}><div className="col">
    <label className="f">Title<input value={title} maxLength={200} onChange={e => setTitle(e.target.value)} autoFocus /></label>
    <div className="grid g2"><label className="f">Assigned to<select value={who} onChange={e => setWho(e.target.value)}><option value="">Nobody</option>{members.map(m => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select></label>
      <label className="f">Due date<input type="date" value={due} onChange={e => setDue(e.target.value)} /></label></div>
    <label className="f">Note<textarea rows={3} value={note} onChange={e => setNote(e.target.value)} /></label>
    <div className="row"><button className="btn" disabled={!title.trim()} onClick={() => onSave({ title, note, ...(who ? { assignee_id: Number(who) } : { clear_assignee: true }), ...(due ? { due_date: due } : { clear_due_date: true }) })}>Save</button><button className="btn ghost" onClick={onClose}>Cancel</button></div></div></Modal>
}

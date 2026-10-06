import { useEffect, useState } from "react"
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"
import { Activity, BarChart3, Boxes, ClipboardCheck, Coins, FileText, FlaskConical, Gauge, Lightbulb, ListChecks, LogOut, Menu, MessageCircle, Package, Settings, Target, TrendingUp, Truck, Upload, Users, X } from "lucide-react"
import { Banner, Loading, Logo } from "../components/ui"
import { useAuth } from "../state/auth"
import { useWs } from "../state/workspace"

type Item = [string, string, any, string | null]   // path, label, icon, required capability
const MAIN: Item[] = [["overview", "Overview", Gauge, null], ["monitoring", "Monitoring", Activity, null], ["decision-center", "Decision Center", Target, null], ["insights", "Insights", Lightbulb, null], ["recommendations", "Recommendations", ClipboardCheck, null], ["actions", "Actions", ListChecks, null]]
const ANALYSIS: Item[] = [["sales", "Sales", BarChart3, "sales"], ["products", "Products", Package, "products"], ["inventory", "Inventory", Boxes, "inventory"], ["customers", "Customers", Users, "customers"], ["suppliers", "Suppliers", Truck, "suppliers"], ["profitability", "Profitability", Coins, "profitability"], ["forecast", "Forecast", TrendingUp, "forecast"], ["what-if", "What-if", FlaskConical, "products"]]

export default function AppLayout() {
  const { user, businesses, logout } = useAuth()
  const { mode, base, bid, setBid, data, loading, readOnly } = useWs()
  const [open, setOpen] = useState(false)
  const nav = useNavigate(); const loc = useLocation()
  useEffect(() => setOpen(false), [loc.pathname])
  useEffect(() => { if (mode === "customer" && !loading && businesses.length === 0 && !loc.pathname.endsWith("/onboarding")) nav("/app/onboarding", { replace: true }) }, [mode, loading, businesses.length, loc.pathname, nav])

  const has = data?.has_data
  const link = (p: string, l: string, I: any) => <NavLink key={p} to={`${base}/${p}`} className={({ isActive }) => "nav" + (isActive ? " on" : "")}><I size={17} />{l}</NavLink>
  const show = (items: Item[]) => items.filter(([, , , cap]) => !cap || (has && data!.capabilities[cap]?.available))
  const side = <aside className={"side" + (open ? " open" : "")} aria-label="Application">
    <Link to={mode === "demo" ? "/" : "/app"} style={{ textDecoration: "none" }}><Logo light /></Link>
    {mode === "customer" && businesses.length > 0 && <div className="biz"><div className="xs" style={{ opacity: .7, marginBottom: 4 }}>Business</div>
      {businesses.length > 1 ? <select value={bid ?? ""} onChange={e => { setBid(Number(e.target.value)); nav("/app/overview") }} aria-label="Business">{businesses.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select> : <b>{businesses[0].name}</b>}</div>}
    {mode === "demo" && <div className="biz"><b>Nova Market</b><div className="xs" style={{ opacity: .8 }}>Demo data — fictional</div></div>}
    {link("overview", "Overview", Gauge)}
    {has && <>{MAIN.slice(1).map(([p, l, I]) => link(p, l, I))}<div className="grp">Your business</div>{show(ANALYSIS).map(([p, l, I]) => link(p, l, I))}<div className="grp">Ask</div>{link("assistant", "Business analyst", MessageCircle)}</>}
    <div className="grp">Manage</div>
    {mode === "customer" && !readOnly && link("import", "Import data", Upload)}
    {mode === "customer" && <>{link("datasets", "My data", Boxes)}{link("reports", "Reports", FileText)}{link("settings", "Settings", Settings)}</>}
    <div style={{ marginTop: "auto", paddingTop: 16 }}>
      {mode === "demo" ? <><Link className="btn acc sm" style={{ width: "100%" }} to="/register">Create my workspace</Link><Link className="btn ghost sm" style={{ width: "100%", color: "#c7d9de" }} to="/">← Back to website</Link></>
        : <><div className="xs" style={{ padding: "0 12px 6px", opacity: .8 }}>{user?.name}<br />{user?.email}</div><button className="btn ghost sm" style={{ width: "100%", color: "#c7d9de", justifyContent: "flex-start" }} onClick={async () => { await logout(); nav("/") }}><LogOut size={16} /> Sign out</button></>}
    </div></aside>

  return <div className="shell">
    <div className="topbar"><button className="btn ghost sm" aria-label="Open menu" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button><Logo /></div>
    {side}
    <main className="main" id="content">
      {mode === "demo" && <div className="mb"><Banner kind="demo">Demo data — fictional. “Nova Market” is an invented company used to show what Business Detective does. <Link to="/register">Create your own workspace</Link></Banner></div>}
      {mode === "customer" && data?.analysis?.stale_currency && <div className="mb"><Banner kind="warn">Your business currency changed after the last analysis. Re-run the analysis in <Link to="/app/settings">Settings</Link> so amounts and insights use the new currency.</Banner></div>}
      {loading && !data && mode === "customer" && businesses.length === 0 ? <Loading /> : <Outlet />}
    </main></div>
}

import { Link } from "react-router-dom"
import { Activity, BellRing, ClipboardCheck, FileText, Lightbulb, LineChart, Lock, Search, ShieldCheck, Upload, Wand2 } from "lucide-react"

export const STEPS: [string, string][] = [
  ["Create your workspace", "Tell us your business name, industry and currency."],
  ["Upload your data", "Drop a CSV or Excel file exported from your till, ERP or spreadsheet."],
  ["We inspect it", "We check quality, flag problems and tell you exactly what they affect."],
  ["Confirm the columns", "We detect what each column means. You can correct anything."],
  ["Analyze", "Business Detective studies trends, unusual days, products, stock, margins and customers."],
  ["Monitor and act", "See what needs attention, why, how much it may cost — and turn it into actions."],
]

export const FEATURES: [any, string, string][] = [
  [Activity, "Business monitor", "One screen that shows whether each part of your business is normal, needs attention or is critical."],
  [Search, "What's unusual", "Spots abnormal sales days and sustained drops by comparing with your own weekday patterns."],
  [LineChart, "What's driving the change", "Shows which products are behind a rise or fall — and says clearly when it is association, not proof."],
  [BellRing, "Stock & supplier alerts", "Estimates days of stock left, flags repeated stockouts and supplier cost increases."],
  [Lightbulb, "Insights you can read", "Every finding explains what happened, why it matters, the impact, the evidence and what to do."],
  [ClipboardCheck, "Decision Center & actions", "A daily priority list. Turn any recommendation into an assigned action with a due date."],
  [Wand2, "What-if simulator", "Try a price, cost or volume change and see an estimate — clearly labelled as a simulation."],
  [FileText, "PDF reports", "Professional reports for partners, banks or your team, generated from your own data."],
  [ShieldCheck, "Your data stays yours", "Private workspaces, protected access and no customer data sent to external AI by default."],
]

export const FAQ: [string, string][] = [
  ["Do I need to install anything?", "No. Business Detective runs in your web browser. You create an account, upload a file and start using it."],
  ["What kind of file can I upload?", "CSV or Excel (.xlsx) files with at least a date and a sales amount (or quantity and unit price). Column names can be in English or French and in any order — we detect them and you can correct them."],
  ["What if my data is incomplete or messy?", "We tell you exactly what we found: missing values, unreadable dates, duplicates, and what each problem affects. Analyses that your data can't support are shown as unavailable instead of being guessed."],
  ["Does it invent numbers?", "Never. Every number comes from your file or from a calculation on it. Estimates (impact, stock cover, forecasts) are labelled as estimates."],
  ["How much history do I need?", "A few weeks already helps. Unusual-day detection, driver analysis and forecasts need at least 28 days. Forecast reliability is tested on your own recent data and shown to you."],
  ["Is my data shared with AI providers?", "No. The assistant answers from the analysis computed inside the platform. An external AI model is an optional add-on that is off by default and, if enabled, only ever receives summarised results — never your raw rows."],
  ["Which currencies are supported?", "Each business picks its own currency (DZD, EUR, USD, GBP and more). Nothing is hardcoded."],
  ["Can my team use it?", "Yes. Invite teammates to your workspace as admin, member or read-only viewer and assign them actions."],
  ["Can I delete my data?", "Yes. You can delete any dataset, report or the whole workspace at any time; the uploaded files are removed with it."],
]

export const Cta = ({ title = "Turn your business data into decisions.", sub = "Create your workspace in minutes. No installation, no code." }) => (
  <section className="section" style={{ background: "#0f4c5c", color: "#fff" }}><div className="wrap center">
    <h2 style={{ color: "#fff" }}>{title}</h2><p style={{ color: "#c7dde3", marginBottom: 22 }}>{sub}</p>
    <div className="row" style={{ justifyContent: "center" }}><Link className="btn acc lg" to="/register">Start analyzing</Link><Link className="btn lg" style={{ background: "transparent", borderColor: "#7fb5c4" }} to="/demo">Explore demo</Link></div></div></section>
)

export const StepsGrid = () => <div className="grid g3">{STEPS.map(([t, d], n) => <div className="card flat row" key={t} style={{ alignItems: "flex-start", flexWrap: "nowrap" }}><span className="step-n">{n + 1}</span><div><b>{t}</b><p className="sm mute" style={{ margin: 0 }}>{d}</p></div></div>)}</div>

export const FeatureGrid = () => <div className="grid g3">{FEATURES.map(([I, t, d]) => <div className="card flat" key={t}><I size={24} color="#0f4c5c" /><h3 style={{ marginTop: 10 }}>{t}</h3><p className="sm mute" style={{ margin: 0 }}>{d}</p></div>)}</div>

export const FaqList = ({ items = FAQ }: { items?: [string, string][] }) => <div className="faq" style={{ maxWidth: 760, margin: "auto" }}>{items.map(([q, a]) => <details key={q}><summary>{q}</summary><p>{a}</p></details>)}</div>

export const Trust = () => <div className="grid g3">
  <div className="card flat"><Lock size={22} color="#0f4c5c" /><h3 style={{ marginTop: 8 }}>Private by design</h3><p className="sm mute" style={{ margin: 0 }}>Each business has its own workspace. Other customers can never see your data, and files are never publicly reachable.</p></div>
  <div className="card flat"><ShieldCheck size={22} color="#0f4c5c" /><h3 style={{ marginTop: 8 }}>Protected access</h3><p className="sm mute" style={{ margin: 0 }}>Passwords are stored hashed, sessions can be ended at any time, and roles control who can change what.</p></div>
  <div className="card flat"><Upload size={22} color="#0f4c5c" /><h3 style={{ marginTop: 8 }}>You stay in control</h3><p className="sm mute" style={{ margin: 0 }}>Delete a dataset, a report or the entire workspace whenever you want. Read our <Link to="/privacy">privacy notice</Link>.</p></div></div>

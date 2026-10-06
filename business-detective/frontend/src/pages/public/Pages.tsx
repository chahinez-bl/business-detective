import { FormEvent, useState } from "react"
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom"
import { Banner } from "../../components/ui"
import { useAuth } from "../../state/auth"
import { Cta, FaqList, FeatureGrid, StepsGrid, Trust } from "./content"

const Head = ({ t, s }: { t: string; s: string }) => <div className="wrap center" style={{ padding: "56px 0 24px" }}><h1>{t}</h1><p className="mute" style={{ maxWidth: 640, margin: "10px auto 0", fontSize: "1.1rem" }}>{s}</p></div>

export const Product = () => <>
  <Head t="Understand. Detect. Decide. Act." s="Business Detective helps businesses understand what is happening, detect what needs attention, understand why it is happening, decide what to do, and take action from one place." />
  <div className="wrap section"><div className="grid g2">
    <div className="card"><h3>For business owners, not analysts</h3><p className="mute">Plain language, clear priorities and progressive detail. If you want the technical calculation, it is one click away under “Details”.</p></div>
    <div className="card"><h3>Honest by design</h3><p className="mute">If your data doesn't support an analysis, we say so. We never invent numbers, and we label every estimate and simulation.</p></div>
    <div className="card"><h3>Flexible with your data</h3><p className="mute">Different businesses have different spreadsheets. Business Detective adapts to the columns you have and shows only what it can support.</p></div>
    <div className="card"><h3>From insight to action</h3><p className="mute">Recommendations become assigned actions with due dates, so problems get fixed instead of just noticed.</p></div></div></div>
  <Cta /></>
export const Features = () => <><Head t="Features" s="Everything you need to monitor your business and decide what to do next." /><div className="wrap section"><FeatureGrid /></div><Cta /></>
export const HowItWorks = () => <><Head t="How it works" s="No installation. No code. Just your data and a browser." /><div className="wrap section"><StepsGrid /></div><Cta /></>
export const Faq = () => <><Head t="Frequently asked questions" s="Straight answers about data, privacy and what Business Detective can and cannot do." /><div className="wrap section"><FaqList /></div><Cta /></>

export const Pricing = () => <><Head t="Pricing" s="Business Detective is in early access. Final plans are not published yet." />
  <div className="wrap section"><div className="grid g3">
    {[["Starter", "For a single small business", ["1 workspace", "CSV and Excel import", "Monitoring, insights and actions", "PDF reports"]],
      ["Growth", "For growing teams", ["Several workspaces", "Team members and roles", "Everything in Starter", "Priority support"]],
      ["Business", "For multi-site operations", ["Custom limits", "Onboarding help", "Optional private AI add-on", "Dedicated support"]]].map(([n, d, f], k) => (
      <div key={n as string} className={"card price" + (k === 1 ? " hot" : "")}><h3>{n as string}</h3><p className="mute">{d as string}</p><div className="b" style={{ fontSize: "1.4rem", margin: "10px 0" }}>Pricing to be announced</div>
        <ul>{(f as string[]).map(x => <li key={x}>{x}</li>)}</ul><Link className="btn sec" to="/register">Join early access</Link></div>))}</div>
    <p className="center mute mt2">This page is a placeholder: no prices are charged and no payment is collected in this version.</p></div></>

export const Privacy = () => <div className="prose"><h1>Privacy notice</h1><p className="mute">Plain-language summary of how Business Detective handles your data.</p>
  <h2>What we store</h2><p>Your account (name, email, password stored only as a salted hash), your business settings, the files you upload, and the results computed from them (insights, recommendations, actions, reports).</p>
  <h2>Who can see it</h2><p>Only members you add to your workspace. Other customers cannot access your data, and uploaded files and reports are never publicly reachable — every request is checked against your account and workspace.</p>
  <h2>AI and third parties</h2><p>The assistant answers using results calculated inside the platform. External AI providers are off by default. If an administrator enables one, only summarised analytical results are sent — never your raw rows — and answers containing numbers that are not in those results are rejected.</p>
  <h2>Your controls</h2><p>You can delete datasets, reports or the entire workspace at any time; the underlying files are deleted with them. You can sign out everywhere by signing out of your session.</p>
  <h2>Logs</h2><p>Server logs record technical errors only. Dataset contents are never written to logs.</p>
  <h2>Questions</h2><p>Use the <Link to="/contact">contact page</Link>. This summary describes the software's behaviour; the operator of the service is responsible for publishing its own legal terms before commercial use.</p></div>

const CONTACT = (import.meta.env.VITE_CONTACT_EMAIL as string | undefined) || ""
export function Contact() {
  const [name, setName] = useState(""); const [msg, setMsg] = useState("")
  const href = `mailto:${CONTACT}?subject=${encodeURIComponent("Business Detective — message from " + name)}&body=${encodeURIComponent(msg)}`
  return <><Head t="Contact" s="Questions, feedback or a demo request? We'd love to hear from you." />
    <div className="wrap section" style={{ maxWidth: 620 }}>{CONTACT ? <div className="card col">
      <label className="f">Your name<input value={name} onChange={e => setName(e.target.value)} /></label>
      <label className="f">Message<textarea rows={5} value={msg} onChange={e => setMsg(e.target.value)} /></label>
      <a className={"btn" + (name && msg ? "" : " sec")} href={name && msg ? href : undefined} aria-disabled={!(name && msg)}>Send by email</a>
      <p className="xs mute" style={{ margin: 0 }}>This opens your email app addressed to {CONTACT}.</p></div>
      : <Banner kind="info">The contact address has not been configured yet. The site owner sets it with the <code>VITE_CONTACT_EMAIL</code> build variable.</Banner>}</div></>
}

function AuthShell({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) {
  return <div className="auth"><div className="card"><h2>{title}</h2><p className="mute">{sub}</p>{children}</div></div>
}

export function Login() {
  const { login, user } = useAuth(); const nav = useNavigate(); const loc = useLocation() as any
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false)
  if (user) return <Navigate to={loc.state?.from ?? "/app"} replace />
  const go = async (e: FormEvent) => { e.preventDefault(); setBusy(true); setErr(""); try { await login(email, pw); nav(loc.state?.from ?? "/app", { replace: true }) } catch (x: any) { setErr(x.message) } setBusy(false) }
  return <AuthShell title="Welcome back" sub="Sign in to your workspace."><form className="col" onSubmit={go}>
    <label className="f">Email<input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></label>
    <label className="f">Password<input type="password" required autoComplete="current-password" value={pw} onChange={e => setPw(e.target.value)} /></label>
    {err && <Banner kind="err">{err}</Banner>}<button className="btn" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    <p className="sm mute center" style={{ margin: 0 }}>New here? <Link to="/register">Create an account</Link></p></form></AuthShell>
}

export function Register() {
  const { register, user } = useAuth(); const nav = useNavigate()
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/app" replace />
  const go = async (e: FormEvent) => { e.preventDefault(); setBusy(true); setErr(""); try { await register(name, email, pw); nav("/app", { replace: true }) } catch (x: any) { setErr(x.message) } setBusy(false) }
  return <AuthShell title="Create your account" sub="Free during early access. No credit card."><form className="col" onSubmit={go}>
    <label className="f">Your name<input required autoComplete="name" value={name} onChange={e => setName(e.target.value)} /></label>
    <label className="f">Work email<input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></label>
    <label className="f">Password<small>At least 8 characters, mixing letters and numbers.</small><input type="password" required minLength={8} autoComplete="new-password" value={pw} onChange={e => setPw(e.target.value)} /></label>
    {err && <Banner kind="err">{err}</Banner>}<button className="btn" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
    <p className="sm mute center" style={{ margin: 0 }}>Already registered? <Link to="/login">Sign in</Link></p></form></AuthShell>
}

export { Trust }

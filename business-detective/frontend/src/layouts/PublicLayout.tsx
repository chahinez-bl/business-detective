import { useState } from "react"
import { Link, NavLink, Outlet, useLocation } from "react-router-dom"
import { Menu, X } from "lucide-react"
import { Logo } from "../components/ui"
import { useAuth } from "../state/auth"

const LINKS: [string, string][] = [["/product", "Product"], ["/features", "Features"], ["/how-it-works", "How it works"], ["/demo", "Demo"], ["/pricing", "Pricing"], ["/faq", "FAQ"], ["/contact", "Contact"]]

export default function PublicLayout() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const loc = useLocation()
  return <>
    <header className="pub-head"><div className="pub-in" style={{ position: "relative" }}>
      <Link to="/" style={{ textDecoration: "none" }}><Logo /></Link>
      <nav className={"pub-nav" + (open ? " open" : "")} aria-label="Main" onClick={() => setOpen(false)}>
        {LINKS.map(([to, l]) => <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "on" : "")}>{l}</NavLink>)}
        <span className="right" />
        {user ? <Link className="btn sm" to="/app">Open my workspace</Link> : <><Link to="/login" className="b">Log in</Link><Link className="btn sm" to="/register">Get started</Link></>}
      </nav>
      <button className="btn ghost burger" aria-label="Menu" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
    </div></header>
    <main key={loc.pathname}><Outlet /></main>
    <footer className="foot"><div className="wrap"><div className="grid">
      <div><Logo light /><p className="sm" style={{ maxWidth: 320, marginTop: 12 }}>Understand what is happening in your business, detect what needs attention, decide what to do and act — from one place.</p></div>
      <div className="col"><b style={{ color: "#fff" }}>Product</b><Link to="/features">Features</Link><Link to="/how-it-works">How it works</Link><Link to="/demo">Demo</Link><Link to="/pricing">Pricing</Link></div>
      <div className="col"><b style={{ color: "#fff" }}>Company</b><Link to="/faq">FAQ</Link><Link to="/contact">Contact</Link><Link to="/privacy">Privacy</Link></div>
      <div className="col"><b style={{ color: "#fff" }}>Account</b><Link to="/login">Log in</Link><Link to="/register">Get started</Link></div>
    </div><p className="xs" style={{ marginTop: 28, opacity: .7 }}>© {new Date().getFullYear()} Business Detective. “Nova Market” is a fictional company used only for the demo.</p></div></footer>
  </>
}

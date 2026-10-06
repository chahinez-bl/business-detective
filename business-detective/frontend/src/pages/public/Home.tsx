import { Link } from "react-router-dom"
import { Cta, FaqList, FeatureGrid, StepsGrid, Trust } from "./content"
import { Sev } from "../../components/ui"

export default function Home() {
  return <>
    <div className="wrap hero">
      <div>
        <span className="badge st-Attention" style={{ marginBottom: 14 }}>Business monitoring & decision support</span>
        <h1>Turn your business data into decisions.</h1>
        <p className="lead">Upload your business data, discover what is changing, understand why, and know what to do next.</p>
        <div className="row mt"><Link className="btn lg" to="/register">Start analyzing</Link><Link className="btn sec lg" to="/demo">Explore demo</Link></div>
        <p className="sm mute mt">No installation. Works in your browser with CSV or Excel files.</p>
      </div>
      <div className="hero-card" aria-label="Example of an alert">
        <div className="row between"><b>Example alert</b><span className="badge st-na">Illustration only</span></div>
        <div className="alert High mt"><div className="row"><Sev s="High" /><span className="xs mute">Sales</span></div>
          <h3 style={{ margin: "8px 0 4px", fontSize: "1.02rem" }}>Sales are well below your usual weekday pattern</h3>
          <p className="sm" style={{ margin: 0 }}>One product accounts for most of the decline. Possible contributing factor: it was out of stock on several days.</p></div>
        <div className="sect mt"><h4>What to do</h4>Check availability and supplier replenishment, then assign the follow-up to a teammate.</div>
        <p className="xs mute" style={{ margin: "10px 0 0" }}>Your real alerts are built from your own uploaded data.</p>
      </div>
    </div>

    <section className="section alt"><div className="wrap"><h2>Most businesses find problems too late</h2>
      <p className="sub">Sales slip, stock runs out, supplier prices creep up, a good customer quietly stops buying. The data is there — in spreadsheets nobody has time to dig through.</p>
      <div className="flow"><span className="p">Your data</span>→<span className="p">Understand</span>→<span className="p">Monitor</span>→<span className="p">Detect</span>→<span className="p">Explain</span>→<span className="p">Decide</span>→<span className="p">Act</span></div></div></section>

    <section className="section"><div className="wrap"><h2>How it works</h2><p className="sub">From a spreadsheet to a monitored business in six simple steps.</p><StepsGrid /></div></section>

    <section className="section alt"><div className="wrap"><h2>Monitoring that tells you where to look</h2>
      <p className="sub">Sales, products, inventory, customers, suppliers and profitability each get a clear status — Normal, Attention, Warning or Critical — and the most important problems come first.</p>
      <div className="grid g2"><div className="card flat"><h3>Insights, not just charts</h3><p className="sm mute">Every finding answers five questions:</p>
        <ul style={{ paddingLeft: 18, margin: 0 }}><li><b>What</b> happened</li><li><b>Why</b> it matters</li><li>What is the <b>impact</b></li><li>What is the <b>evidence</b></li><li>What <b>to do</b></li></ul></div>
        <div className="card flat"><h3>Recommendations that become actions</h3><p className="sm mute">The Decision Center answers “What should I do today?”. Turn any recommendation into an action, assign it, set a due date and track it to done.</p></div></div></div></section>

    <section className="section"><div className="wrap"><h2>Everything in one place</h2><p className="sub">A complete toolkit for business owners — no data science needed.</p><FeatureGrid />
      <div className="center mt2"><Link className="btn sec" to="/demo">See an example analysis (demo data — fictional)</Link></div></div></section>

    <section className="section alt"><div className="wrap"><h2>Security and privacy</h2><p className="sub">Your business data is sensitive. We treat it that way.</p><Trust /></div></section>

    <section className="section"><div className="wrap"><h2>Simple pricing, coming soon</h2><p className="sub">We're in early access. <Link to="/pricing">See what to expect</Link>.</p></div></section>
    <section className="section alt"><div className="wrap"><h2>Questions</h2><div className="mt"><FaqList items={undefined} /></div></div></section>
    <Cta />
  </>
}

import { Link } from "react-router-dom"
import { Banner, Needs, PageHead, Stat } from "../../components/ui"
import { Bars, ForecastChart, RevenueChart } from "../../components/charts"
import { Change } from "../../components/ui"
import { money, moneyShort, num, pct } from "../../lib/format"

const Risk = ({ r }: { r: string }) => <span className={`badge sev-${r === "HIGH" ? "High" : r === "MEDIUM" ? "Medium" : "Low"}`}>{r.charAt(0) + r.slice(1).toLowerCase()}</span>

export const Sales = () => <Needs cap="sales">{d => {
  const p = d.kpis.period, rc = d.root_cause, cur = d.currency
  return <><PageHead title="Sales" sub="How your revenue is moving." />
    <div className="grid g4 mb"><Stat label="Total revenue" value={moneyShort(d.kpis.revenue, cur)} sub={`${d.kpis.days} days`} />
      <Stat label="Average per day" value={moneyShort(d.kpis.avg_daily_revenue, cur)} />
      {p && <Stat label={`Last ${p.days} days`} value={moneyShort(p.revenue, cur)} sub={<><Change v={p.revenue_change_pct} /> vs previous {p.days} days</>} />}
      {d.kpis.units != null && <Stat label="Units sold" value={num(d.kpis.units)} />}</div>
    <h2>Daily revenue</h2><div className="card"><RevenueChart data={d.daily} cur={cur} /></div>
    <div className="grid g2 mt2"><div><h2>By month</h2><div className="card"><Bars data={d.monthly} x="month" y="revenue" cur={cur} />{d.monthly.some(m => m.partial) && <p className="xs mute" style={{ margin: 0 }}>Partial months are not complete months of data.</p>}</div></div>
      <div><h2>Busiest days</h2><div className="card"><Bars data={d.weekday} x="day" y="avg_revenue" cur={cur} color="#f2b134" /><p className="xs mute" style={{ margin: 0 }}>Average revenue per weekday.</p></div></div></div>
    {rc ? <><h2 className="mt2">What's driving the change?</h2><div className="card"><p>Revenue in the last {rc.window_days} days was <b>{money(rc.revenue_current, cur)}</b> versus <b>{money(rc.revenue_previous, cur)}</b> in the {rc.window_days} days before (<b className={rc.change_pct >= 0 ? "up" : "down"}>{pct(rc.change_pct, true)}</b>).</p>
      {rc.contributors.length > 0 && <><Bars data={rc.contributors} x="name" y="delta" horizontal height={220} fmt={v => money(v, cur)} color="#c4560a" /><p className="xs mute" style={{ margin: 0 }}>Change in revenue by {rc.dimension}. This shows where the change is concentrated; it does not prove the cause.</p></>}</div></>
      : <div className="mt2"><Banner kind="info">{d.capabilities.contribution.reason || "Not enough data to calculate this metric."}</Banner></div>}</>
}}</Needs>

export const Products = () => <Needs cap="products">{d => {
  const cur = d.currency, hasM = d.products.some(p => p.margin_pct != null)
  return <><PageHead title="Products" sub="Which products drive your revenue — and which are changing." />
    <div className="card pad0 tw"><table><thead><tr><th>Product</th><th>Revenue</th><th>Share</th>{d.products[0]?.units != null && <><th>Units</th><th>Avg price</th></>}{hasM && <th>Margin</th>}</tr></thead>
      <tbody>{d.products.map(p => <tr key={p.product}><td className="b">{p.product}</td><td>{money(p.revenue, cur)}</td><td>{pct(p.share_pct, false, 1)}</td>{p.units != null && <><td>{num(p.units)}</td><td>{money(p.avg_price, cur)}</td></>}{hasM && <td className={p.margin_pct != null && p.margin_pct < 0 ? "down b" : ""}>{pct(p.margin_pct)}</td>}</tr>)}</tbody></table></div>
    {d.insights.filter(i => i.area === "Products").length > 0 && <><h2 className="mt2">Changes worth knowing</h2><div className="col">{d.insights.filter(i => i.area === "Products").map(i => <div key={i.id} className={"alert " + (i.category === "Opportunity" ? "Opportunity" : i.severity)}><b>{i.title}</b><p className="sm" style={{ margin: "4px 0 0" }}>{i.what} <Link to={`../insights/${i.id}`}>Details</Link></p></div>)}</div></>}</>
}}</Needs>

export const Inventory = () => <Needs cap="inventory">{d => <><PageHead title="Inventory" sub="Which products may run out — and when." />
  <div className="card pad0 tw"><table><thead><tr><th>Product</th><th>In stock</th><th>Sold per day</th><th>Demand trend</th><th>Estimated cover</th><th>Stockout days</th><th>Risk</th></tr></thead>
    <tbody>{d.inventory.map(i => <tr key={i.product}><td className="b">{i.product}</td><td>{num(i.stock)}</td><td>{num(i.daily_demand, 1)}</td><td>{i.demand_trend_pct != null ? pct(i.demand_trend_pct, true, 0) : "—"}</td><td>{i.stock <= 0 ? <b className="down">Out of stock</b> : i.range}</td><td>{i.stockout_days}</td><td><Risk r={i.risk} /></td></tr>)}</tbody></table></div>
  <p className="sm mute mt">Cover is an estimate: current stock divided by average daily sales over the last 14 days. It assumes no delivery is already on the way.</p></>}</Needs>

export const Customers = () => <Needs cap="customers">{d => { const c = d.customers, cur = d.currency; return <><PageHead title="Customers" sub="Who buys from you, and whether they keep coming back." />
  <div className="grid g4 mb"><Stat label="Customers" value={num(c.total)} />{c.active_current != null && <Stat label={`Active, last ${c.window_days} days`} value={num(c.active_current)} sub={`${num(c.active_previous)} in the previous ${c.window_days} days`} />}
    {c.lost != null && <Stat label="Did not return" value={num(c.lost)} sub={`${num(c.new)} new customers`} tone={c.lost > c.new ? "down" : undefined} />}<Stat label="Top customer share" value={pct(c.top1_share_pct, false, 0)} sub={`Top 5: ${pct(c.top5_share_pct, false, 0)}`} /></div>
  <div className="card pad0 tw"><table><thead><tr><th>Customer</th><th>Revenue</th><th>Share</th><th>Orders</th><th>Last purchase</th></tr></thead><tbody>{c.top.map((t: any) => <tr key={t.name}><td className="b">{t.name}</td><td>{money(t.revenue, cur)}</td><td>{pct(t.share_pct, false, 1)}</td><td>{t.orders}</td><td>{t.last_purchase} <span className="xs mute">({t.days_since} days ago)</span></td></tr>)}</tbody></table></div></> }}</Needs>

export const Suppliers = () => <Needs cap="suppliers">{d => { const cur = d.currency; return <><PageHead title="Suppliers" sub="Who supplies your products and how their costs are changing." />
  <div className="card pad0 tw"><table><thead><tr><th>Supplier</th><th>Share of revenue</th><th>Products</th><th>Largest cost change</th><th>Status</th></tr></thead><tbody>{d.suppliers.map(s => <tr key={s.supplier}><td className="b">{s.supplier}</td><td>{pct(s.share_pct, false, 0)}</td><td>{s.products ?? "—"}</td><td>{s.max_cost_change_pct != null ? pct(s.max_cost_change_pct, true) : "—"}</td><td><span className={`badge st-${s.status}`}>{s.status}</span></td></tr>)}</tbody></table></div>
  {d.supplier_drift.length > 0 ? <><h2 className="mt2">Purchase cost changes</h2><div className="card pad0 tw"><table><thead><tr><th>Supplier</th><th>Product</th><th>Before</th><th>Recent</th><th>Change</th></tr></thead><tbody>{[...d.supplier_drift].sort((a, b) => b.cost_change_pct - a.cost_change_pct).map((x, k) => <tr key={k}><td>{x.supplier}</td><td>{x.product}</td><td>{money(x.avg_cost_before, cur)}</td><td>{money(x.avg_cost_recent, cur)}</td><td className={x.cost_change_pct > 5 ? "down b" : ""}>{pct(x.cost_change_pct, true)}</td></tr>)}</tbody></table></div></>
    : <div className="mt"><Banner kind="info">Cost changes can't be tracked: {d.capabilities.profitability.available ? "there isn't enough history per supplier." : "your data has no purchase cost column."}</Banner></div>}</> }}</Needs>

export const Profitability = () => <Needs cap="profitability">{d => { const p = d.profitability, cur = d.currency; const prods = d.products.filter(x => x.margin_pct != null); return <><PageHead title="Profitability" sub="Where your money is actually made." />
  <div className="grid g4 mb"><Stat label="Gross profit" value={moneyShort(p.profit, cur)} /><Stat label="Gross margin" value={pct(p.margin_pct)} sub={p.margin_change_pts != null ? `${p.margin_change_pts >= 0 ? "+" : ""}${p.margin_change_pts.toFixed(1)} pts vs previous period` : undefined} tone={p.margin_change_pts != null && p.margin_change_pts < 0 ? "down" : "up"} /><Stat label="Revenue with known cost" value={pct(p.revenue_coverage_pct, false, 0)} sub="Profit uses only rows where cost is known" /></div>
  {prods.length > 0 && <><h2>Margin by product</h2><div className="card"><Bars data={prods} x="product" y="margin_pct" horizontal height={Math.max(180, prods.length * 38)} fmt={v => v.toFixed(1) + "%"} color="#0f4c5c" /></div>
    <div className="card pad0 tw mt"><table><thead><tr><th>Product</th><th>Revenue</th><th>Share of revenue</th><th>Profit</th><th>Margin</th></tr></thead><tbody>{prods.map(x => <tr key={x.product}><td className="b">{x.product}</td><td>{money(x.revenue, cur)}</td><td>{pct(x.share_pct, false, 0)}</td><td className={x.profit < 0 ? "down b" : ""}>{money(x.profit, cur)}</td><td className={x.margin_pct < 0 ? "down b" : ""}>{pct(x.margin_pct)}</td></tr>)}</tbody></table></div></>}
  {d.monthly.some(m => m.margin_pct != null) && <><h2 className="mt2">Margin by month</h2><div className="card"><Bars data={d.monthly.filter(m => m.margin_pct != null)} x="month" y="margin_pct" fmt={v => v.toFixed(1) + "%"} color="#f2b134" /></div></>}
  {d.leaks.length > 0 && <><h2 className="mt2">Money leaking away <span className="mute sm">(monthly estimates; some may overlap)</span></h2><div className="card pad0 tw"><table><thead><tr><th>Type</th><th>Item</th><th>Per month</th><th>Basis</th></tr></thead><tbody>{d.leaks.map((l, k) => <tr key={k}><td>{l.type}</td><td>{l.item}</td><td>{money(l.monthly, cur)}</td><td className="mute sm">{l.note}</td></tr>)}</tbody></table></div></>}</> }}</Needs>

export const Forecast = () => <Needs cap="forecast">{d => { const f = d.forecast; if (!f.available) return <Banner kind="info">{f.message}</Banner>; const tot = f.forecast.reduce((s: number, p: any) => s + p.value, 0)
  return <><PageHead title="What may happen next" sub={`An estimate of your revenue for the next ${f.forecast.length} days.`} />
    {f.quality !== "moderate" && <div className="mb"><Banner kind="warn">{f.quality_note}</Banner></div>}
    <div className="grid g3 mb"><Stat label={`Expected revenue, next ${f.forecast.length} days`} value={moneyShort(tot, d.currency)} sub="Estimate, not a guarantee" />
      <Stat label="How reliable is it?" value={f.quality === "moderate" ? "Moderate" : f.quality === "low" ? "Low" : "Limited"} sub={f.backtest_error_pct != null ? `Tested on your last 14 days: off by ~${f.backtest_error_pct.toFixed(0)}%` : "Not enough history to test it"} /></div>
    <div className="card"><ForecastChart history={f.history} forecast={f.forecast} cur={d.currency} /><p className="xs mute" style={{ margin: "6px 0 0" }}>Dashed line: expected. Shaded band: likely range. {f.method}</p></div></> }}</Needs>

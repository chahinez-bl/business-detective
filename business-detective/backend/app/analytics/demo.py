"""Deterministic demo dataset for fictional 'Nova Market'. Patterns are planted in the raw data only;
the analytics engine has to discover them."""
import numpy as np, pandas as pd

def generate(days=120, seed=7):
    r = np.random.default_rng(seed)
    start = pd.Timestamp("2026-05-01")
    # name, base demand, price, cost, supplier, stock0, reorder, lot, lead
    P = [("Olive Oil 1L",14,900,620,"Sahel Foods",120,40,120,4),("Couscous 2kg",18,450,330,"Sahel Foods",160,50,160,4),
         ("Energy Drink",20,180,95,"Atlas Drinks",400,120,400,3),("Premium Coffee",9,1900,1350,"Aroma Import",90,30,90,6),
         ("Bottled Water 6x",25,260,200,"Atlas Drinks",260,80,260,3),("Detergent 3kg",8,1100,700,"CleanCo",80,25,80,5),
         ("Fresh Pasta",12,300,120,"Sahel Foods",60,45,30,5),("Chocolate Bar",16,220,150,"Aroma Import",100,30,100,5)]
    rows, oid = [], 1000
    for name, base, price, cost, sup, s0, rop, lot, lead in P:
        if name not in ("Premium Coffee", "Fresh Pasta", "Energy Drink"): s0, rop, lot = s0 * 2, int(rop * 1.8), lot * 3
        stock, pending = s0, []
        for d in range(days):
            date = start + pd.Timedelta(days=d)
            if date.weekday() >= 4: m = 1.6 if name in ("Energy Drink", "Chocolate Bar") else 1.15
            else: m = 1.0
            t = 1.0
            if name == "Detergent 3kg": t = 1 - 0.55 * d / days            # declining
            if name == "Energy Drink": t = 1 + 0.9 * d / days              # rising demand
            if d == 85: m *= 2.3                                          # unusual sales day
            demand = r.poisson(base * m * t)
            stock += sum(q for a, q in pending if a == d)
            pending = [(a, q) for a, q in pending if a > d]
            sold = min(demand, stock); stock -= sold
            if stock <= rop and not pending: pending.append((d + lead, lot))
            c = cost
            if name == "Premium Coffee" and d > days - 56: c = cost * (1 + 0.14 * (d - (days - 56)) / 56)  # supplier increase
            p = 0.02 + (0.12 * d / days if name == "Chocolate Bar" else 0)                                # rising returns
            ret = int(r.binomial(sold, p)) if sold else 0
            oid += 1
            rows.append(dict(date=date.date().isoformat(), order_id=oid, product=name, quantity=int(sold), selling_price=price,
                             purchase_cost=round(c, 1), supplier=sup, stock=int(stock), returned=ret))
    return pd.DataFrame(rows)

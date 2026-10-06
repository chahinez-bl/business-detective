"""Column detection: maps arbitrary customer headers (EN/FR, snake/camel/spaced) onto canonical business fields."""
import difflib
import re
import unicodedata

import pandas as pd

# key -> (label, help text shown in the mapping wizard)
FIELDS: dict[str, tuple[str, str]] = {
    "date": ("Date", "The day of the sale or transaction."),
    "revenue": ("Revenue / sales amount", "Money received for the line (total, not per unit). Optional if you have quantity and unit price."),
    "product": ("Product / item", "What was sold."),
    "quantity": ("Quantity sold", "Units sold on the line."),
    "price": ("Unit selling price", "Price per unit. Optional if you have a revenue column."),
    "cost": ("Unit purchase cost", "What one unit costs you to buy or produce (per unit). Enables profit and margin."),
    "category": ("Category", "Product family or department."),
    "stock": ("Stock on hand", "Units in stock when the row was recorded. Enables stockout risk."),
    "supplier": ("Supplier", "Who supplies the product."),
    "customer": ("Customer", "Customer name or ID. Enables customer analysis."),
    "returned": ("Returned quantity", "Units returned. Enables return-rate monitoring."),
    "order_id": ("Order / transaction ID", "Identifies the order. Helps avoid treating repeated lines as duplicates."),
    "location": ("Store / location", "Branch, city or store."),
}
PRIORITY = list(FIELDS)

ALIASES: dict[str, list[str]] = {
    "date": ["date", "order_date", "transaction_date", "sale_date", "sales_date", "invoice_date", "day", "jour", "date_vente", "date_commande",
             "date_transaction", "date_facture", "timestamp", "datetime", "purchase_date", "created_at"],
    "revenue": ["revenue", "sales", "sales_amount", "amount", "total", "total_amount", "total_revenue", "turnover", "ca", "chiffre_d_affaires",
                "chiffre_affaires", "montant", "montant_ttc", "montant_ht", "total_ttc", "total_ht", "net_sales", "gross_sales", "line_total", "vente", "ventes"],
    "product": ["product", "product_name", "item", "item_name", "name", "produit", "nom_produit", "article", "designation", "libelle", "sku", "description"],
    "quantity": ["quantity", "qty", "units", "units_sold", "quantite", "qte", "quantite_vendue", "nb_unites", "volume", "pieces", "quantity_sold"],
    "price": ["price", "unit_price", "selling_price", "prix", "prix_vente", "prix_unitaire", "prix_de_vente", "pu", "sale_price"],
    "cost": ["cost", "unit_cost", "purchase_cost", "cout", "cout_achat", "prix_achat", "cout_unitaire", "buying_price", "purchase_price"],
    "category": ["category", "categorie", "product_category", "famille", "family", "rayon", "department", "group"],
    "stock": ["stock", "inventory", "stock_level", "inventaire", "niveau_stock", "on_hand", "stock_on_hand", "qte_stock", "stock_qty", "quantity_on_hand"],
    "supplier": ["supplier", "vendor", "fournisseur", "supplier_name", "nom_fournisseur"],
    "customer": ["customer", "customer_name", "client", "nom_client", "customer_id", "client_id", "id_client", "buyer", "account"],
    "returned": ["returned", "returns", "returned_qty", "retour", "retours", "quantite_retournee", "return_qty", "qty_returned"],
    "order_id": ["order_id", "order", "order_no", "order_number", "transaction_id", "invoice", "invoice_no", "num_commande", "id_commande",
                 "commande", "numero_commande", "receipt", "ticket"],
    "location": ["location", "store", "branch", "city", "wilaya", "magasin", "region", "ville", "shop", "site"],
}


def norm(c) -> str:
    """'TransactionDate' / 'Prix de vente' / 'Quantité' -> 'transaction_date' / 'prix_de_vente' / 'quantite'."""
    t = unicodedata.normalize("NFKD", str(c)).encode("ascii", "ignore").decode()
    t = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", t)
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_").lower()
    return t


def _score(col_norm: str, alias: str) -> int:
    if col_norm == alias:
        return 100
    ct, at = set(col_norm.split("_")), set(alias.split("_"))
    if at <= ct:
        return 60 + 5 * len(at)
    if len(alias) >= 4 and difflib.SequenceMatcher(None, col_norm, alias).ratio() >= 0.88:
        return 55
    return 0


def detect_mapping(df: pd.DataFrame) -> dict[str, str]:
    cols = [str(c) for c in df.columns]
    cn = {c: norm(c) for c in cols}
    cands = []
    for f in PRIORITY:
        for c in cols:
            best = max((_score(cn[c], a) for a in ALIASES[f]), default=0)
            if best >= 50:
                cands.append((best, -PRIORITY.index(f), f, c))
    mapping, used = {}, set()
    for s, _, f, c in sorted(cands, reverse=True):
        if f not in mapping and c not in used:
            mapping[f] = c
            used.add(c)
    if "date" not in mapping:                                   # content-based fallback: a column that parses as dates
        for c in cols:
            if c in used:
                continue
            s = df[c].dropna().astype(str).head(200)
            if len(s) >= 5 and s.str.contains(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}").mean() > 0.8:
                if pd.to_datetime(s, errors="coerce", format="mixed").notna().mean() > 0.8:
                    mapping["date"] = c
                    break
    return mapping


class MappingError(ValueError):
    """Raised with a message that is safe to show to the customer."""


def check_mapping(mapping: dict, columns: list[str]) -> dict[str, str]:
    if not isinstance(mapping, dict):
        raise MappingError("The column mapping is not valid.")
    clean = {k: v for k, v in mapping.items() if v}
    unknown = [k for k in clean if k not in FIELDS]
    if unknown:
        raise MappingError("Unknown field(s) in the mapping: " + ", ".join(map(str, unknown)))
    missing = [v for v in clean.values() if v not in columns]
    if missing:
        raise MappingError("These columns do not exist in your file: " + ", ".join(map(str, missing)))
    if len(set(clean.values())) != len(clean):
        raise MappingError("The same column cannot be used for two different fields.")
    return clean

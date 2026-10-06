import { Navigate, Route } from "react-router-dom"
import Actions from "./Actions"
import { Customers, Forecast, Inventory, Products, Profitability, Sales, Suppliers } from "./Analysis"
import { Datasets, Import } from "./Data"
import { DecisionCenter, InsightDetail, Insights, Recommendations } from "./Insights"
import { Onboarding, Reports, Settings } from "./Manage"
import Monitoring from "./Monitoring"
import Overview from "./Overview"
import { Assistant, WhatIf } from "./Tools"

/** Shared by /app (customer workspace) and /demo (fictional Nova Market): the same pages, different data source. */
export const common = (
  <>
    <Route index element={<Navigate to="overview" replace />} />
    <Route path="overview" element={<Overview />} />
    <Route path="monitoring" element={<Monitoring />} />
    <Route path="decision-center" element={<DecisionCenter />} />
    <Route path="insights" element={<Insights />} />
    <Route path="insights/:id" element={<InsightDetail />} />
    <Route path="recommendations" element={<Recommendations />} />
    <Route path="actions" element={<Actions />} />
    <Route path="sales" element={<Sales />} />
    <Route path="products" element={<Products />} />
    <Route path="inventory" element={<Inventory />} />
    <Route path="customers" element={<Customers />} />
    <Route path="suppliers" element={<Suppliers />} />
    <Route path="profitability" element={<Profitability />} />
    <Route path="forecast" element={<Forecast />} />
    <Route path="what-if" element={<WhatIf />} />
    <Route path="assistant" element={<Assistant />} />
  </>
)
export const customerOnly = (
  <>
    <Route path="onboarding" element={<Onboarding />} />
    <Route path="import" element={<Import />} />
    <Route path="datasets" element={<Datasets />} />
    <Route path="reports" element={<Reports />} />
    <Route path="settings" element={<Settings />} />
  </>
)

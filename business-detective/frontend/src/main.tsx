import { Component, ReactNode, StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import App from "./App"
import { AuthProvider } from "./state/auth"
import "./styles.css"

class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    return this.state.failed
      ? <div style={{ padding: 60, textAlign: "center" }}><h2>Something went wrong</h2><p>Please reload the page. If it keeps happening, contact support.</p><button className="btn" onClick={() => location.reload()}>Reload</button></div>
      : this.props.children
  }
}
createRoot(document.getElementById("root")!).render(<StrictMode><Boundary><BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter></Boundary></StrictMode>)

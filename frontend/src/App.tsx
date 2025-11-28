import React from "react";
import { MachinesProvider } from "./contexts/MachinesContext";
import { ErrorBoundary } from "./components/ErrorBoundary";

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <MachinesProvider>
        <div style={{
          background:"linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)", 
          minHeight:"100vh", 
          color:"#e5e7eb", 
          padding:"40px min(80px, 5vw)",
          fontFamily:"ui-sans-serif",
          overflowX:"hidden"
        }}>
          {/* Header */}
          <header style={{
            marginBottom:40, 
            textAlign:"center",
            paddingBottom:24,
            borderBottom:"2px solid rgba(255,255,255,0.1)"
          }}>
            <h1 style={{fontSize:36, fontWeight:700, marginBottom:8, letterSpacing:"-0.02em"}}>
              CNC-Genius Telemetria
            </h1>
            <p style={{fontSize:14, opacity:0.6, margin:0}}>
              Monitoramento em tempo real • Atualização a cada 1s
            </p>
          </header>

          {/* Main Content */}
          <main style={{maxWidth:"min(1760px, 95vw)", margin:"0 auto", width:"100%"}}>
            {/* Placeholder for Machine Selector */}
            <section style={{marginBottom:32}}>
              <div style={{
                background:"rgba(31,41,55,0.5)", 
                border:"1px solid #374151", 
                borderRadius:12, 
                padding:24, 
                textAlign:"center"
              }}>
                <h2 style={{fontSize:18, fontWeight:600, marginBottom:8, color:"#e5e7eb"}}>
                  Machine Selector
                </h2>
                <p style={{fontSize:14, opacity:0.6, margin:0}}>
                  Component will be loaded here
                </p>
              </div>
            </section>

            {/* Dashboard Grid */}
            <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(300px, 1fr))", gap:24, marginBottom:32}}>
              {/* Placeholder Cards */}
              <div style={{
                background:"rgba(31,41,55,0.5)", 
                border:"1px solid #374151", 
                borderRadius:12, 
                padding:24, 
                textAlign:"center"
              }}>
                <h3 style={{fontSize:16, fontWeight:600, marginBottom:8, color:"#e5e7eb"}}>
                  Machine State
                </h3>
                <p style={{fontSize:14, opacity:0.6, margin:0}}>
                  Status: Loading...
                </p>
              </div>

              <div style={{
                background:"rgba(31,41,55,0.5)", 
                border:"1px solid #374151", 
                borderRadius:12, 
                padding:24, 
                textAlign:"center"
              }}>
                <h3 style={{fontSize:16, fontWeight:600, marginBottom:8, color:"#e5e7eb"}}>
                  Box Health
                </h3>
                <p style={{fontSize:14, opacity:0.6, margin:0}}>
                  System OK
                </p>
              </div>
            </div>

            {/* OEE Card Placeholder */}
            <section style={{marginBottom:32}}>
              <div style={{
                background:"rgba(31,41,55,0.5)", 
                border:"1px solid #374151", 
                borderRadius:12, 
                padding:24, 
                textAlign:"center"
              }}>
                <h2 style={{fontSize:18, fontWeight:600, marginBottom:8, color:"#e5e7eb"}}>
                  OEE Metrics
                </h2>
                <p style={{fontSize:14, opacity:0.6, margin:0}}>
                  Data will be displayed here
                </p>
              </div>
            </section>

            {/* Footer */}
            <footer style={{
              marginTop:40, 
              paddingTop:24,
              borderTop:"1px solid rgba(255,255,255,0.05)",
              fontSize:12, 
              opacity:0.5, 
              textAlign:"center"
            }}>
              <div>Polling: 2s (máquinas) | 1s (status) | API: http://localhost:8001</div>
              <div style={{marginTop:8}}>CNC-Genius Telemetria v0.2 • Dashboard • 1920×1080</div>
            </footer>
          </main>
        </div>
      </MachinesProvider>
    </ErrorBoundary>
  );
};

export default App;

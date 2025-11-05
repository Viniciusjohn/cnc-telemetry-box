import { useEffect, useState } from "react";
import { fetchMachineStatus, MachineStatus, ApiError } from "./lib/api";
import { OEECard } from "./components/OEECard";

const MACHINE_ID = "CNC-SIM-001";
const POLL_INTERVAL_MS = 2000;

export default function App() {
  const [status, setStatus] = useState<MachineStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function poll() {
      try {
        const data = await fetchMachineStatus(MACHINE_ID);
        if (isMounted) {
          setStatus(data);
          setError(null);
          setIsLoading(false);
        }
      } catch (e) {
        if (isMounted) {
          if (e instanceof ApiError) {
            setError(`HTTP ${e.status}: ${e.message}`);
          } else {
            setError(e instanceof Error ? e.message : "Unknown error");
          }
          setIsLoading(false);
        }
      }
    }

    poll();
    const intervalId = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  return (
    <main style={{
      background:"linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)", 
      minHeight:"100vh", 
      color:"#e5e7eb", 
      padding:"40px 80px",
      fontFamily:"ui-sans-serif"
    }}>
      {/* Container centralizado para 1920x1080 */}
      <div style={{maxWidth:1760, margin:"0 auto"}}>
        <header style={{
          marginBottom:40, 
          display:"flex", 
          justifyContent:"space-between", 
          alignItems:"center",
          paddingBottom:24,
          borderBottom:"2px solid rgba(255,255,255,0.1)"
        }}>
          <div>
            <h1 style={{fontSize:36, fontWeight:700, marginBottom:8, letterSpacing:"-0.02em"}}>
              CNC Telemetry Dashboard
            </h1>
            <p style={{fontSize:14, opacity:0.6, margin:0}}>
              Monitoramento em tempo real • Atualização a cada 2s
            </p>
          </div>
          <div style={{
            background:"rgba(59, 130, 246, 0.1)",
            border:"1px solid rgba(59, 130, 246, 0.3)",
            padding:"12px 24px",
            borderRadius:12,
            textAlign:"right"
          }}>
            <div style={{fontSize:12, opacity:0.7, marginBottom:4}}>Máquina</div>
            <div style={{fontSize:18, fontWeight:600, color:"#3b82f6"}}>
              {status?.machine_id || "—"}
            </div>
          </div>
        </header>

      {error && (
        <div style={{background:"rgba(220,38,38,0.2)", border:"1px solid #dc2626", borderRadius:8, padding:16, marginBottom:16}}>
          <strong>Erro:</strong> {error}
        </div>
      )}

      {isLoading && !status && (
        <div style={{textAlign:"center", padding:32, opacity:0.5}}>
          Carregando...
        </div>
      )}

      {/* Status Cards Grid - Otimizado para 1920x1080 */}
      <section style={{
        display:"grid", 
        gridTemplateColumns:"repeat(4, 1fr)", 
        gap:24, 
        marginBottom:32
      }}>
        <Card 
          title="RPM" 
          value={status?.rpm.toFixed(1) ?? "—"} 
          suffix="rev/min"
          color={getStateColor(status?.state)}
        />
        <Card 
          title="Feed" 
          value={status?.feed_mm_min.toFixed(1) ?? "—"} 
          suffix="mm/min"
        />
        <Card 
          title="Estado" 
          value={formatState(status?.state)}
          color={getStateColor(status?.state)}
        />
        <Card 
          title="Atualizado" 
          value={status ? formatTime(status.updated_at) : "—"}
        />
      </section>

      {/* OEE Card - Full Width */}
      <section style={{marginBottom:32}}>
        <OEECard machineId={MACHINE_ID} />
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
        <div>Polling: {POLL_INTERVAL_MS / 1000}s | API: {import.meta.env.VITE_API_BASE || 'http://localhost:8001'}</div>
        <div style={{marginTop:8}}>CNC Telemetry v1.0 • Dashboard otimizado para 1920×1080</div>
      </footer>

      </div> {/* Fim do container centralizado */}
    </main>
  );
}

interface CardProps {
  title: string;
  value: string;
  suffix?: string;
  color?: string;
}

function Card({ title, value, suffix, color }: CardProps) {
  return (
    <div style={{
      background:"linear-gradient(135deg, #1f2937 0%, #111827 100%)", 
      padding:"28px 24px", 
      borderRadius:20, 
      border:"1px solid #374151",
      boxShadow:"0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
      transition:"all 0.3s ease",
      position:"relative" as const,
      overflow:"hidden"
    }}>
      {/* Brilho sutil de fundo */}
      <div style={{
        position:"absolute",
        top:0,
        right:0,
        width:"100px",
        height:"100px",
        background:"radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%)",
        pointerEvents:"none"
      }} />
      
      <div style={{
        fontSize:13, 
        opacity:0.7, 
        marginBottom:12, 
        textTransform:"uppercase", 
        letterSpacing:"0.08em",
        fontWeight:600,
        position:"relative" as const
      }}>
        {title}
      </div>
      <div style={{
        fontSize:42, 
        fontWeight:700, 
        color: color || "#e5e7eb",
        lineHeight:1,
        marginBottom:8,
        position:"relative" as const
      }}>
        {value}
      </div>
      {suffix && (
        <div style={{
          fontSize:13, 
          opacity:0.6, 
          marginTop:8,
          position:"relative" as const
        }}>
          {suffix}
        </div>
      )}
    </div>
  );
}

function formatState(state?: string): string {
  if (!state) return "—";
  switch (state) {
    case "running":
      return "RODANDO";
    case "stopped":
      return "PARADA";
    case "idle":
      return "OCIOSA";
    default:
      return state.toUpperCase();
  }
}

function getStateColor(state?: string): string {
  switch (state) {
    case "running":
      return "#10b981"; // green
    case "stopped":
      return "#ef4444"; // red
    case "idle":
      return "#f59e0b"; // yellow
    default:
      return "#e5e7eb"; // gray
  }
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

import { useEffect, useState } from "react";
import { fetchMachineEvents, MachineEvent, ApiError } from "./lib/api";
import { OEECard } from "./components/OEECard";
import { MachineSelector } from "./components/MachineSelector";
import { BoxHealth } from "./components/BoxHealth";
import { MachineStateCard } from "./components/MachineStateCard";
import { ErrorBoundary, NetworkErrorFallback, DataErrorFallback } from "./components/ErrorBoundary";
import { useMachines } from "./contexts/MachinesContext";
import { MachinesProvider } from "./contexts/MachinesContext";

const EVENTS_POLL_INTERVAL_MS = 10000; // 10s para eventos

function AppContent() {
  const { 
    selectedMachineId, 
    selectedMachineStatus, 
    selectedMachineLoading, 
    selectedMachineError,
    machinesError 
  } = useMachines();
  
  const [events, setEvents] = useState<MachineEvent[]>([]);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'health'>('dashboard');

  // Error boundary handler
  const handleError = (error: Error, errorInfo: any) => {
    console.error('App error:', error, errorInfo);
    // Opcional: enviar para serviço de monitoring
  };

  // Poll events for selected machine
  useEffect(() => {
    if (!selectedMachineId) {
      setEvents([]);
      setEventsError(null);
      return;
    }

    let isMounted = true;

    async function fetchEvents() {
      try {
        const eventsData = await fetchMachineEvents(selectedMachineId, 20);
        if (isMounted) {
          setEvents(eventsData);
          setEventsError(null);
        }
      } catch (e) {
        if (isMounted) {
          if (e instanceof ApiError) {
            setEventsError(`HTTP ${e.status}: ${e.message}`);
          } else {
            setEventsError(e instanceof Error ? e.message : "Unknown error");
          }
          setEvents([]);
        }
      }
    }

    // Initial fetch
    fetchEvents();
    
    // Set up polling
    const interval = setInterval(fetchEvents, EVENTS_POLL_INTERVAL_MS);
    
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedMachineId]);

  // Determine connection status based on selected machine status
  const getConnectionStatus = () => {
    if (!selectedMachineStatus) return "disconnected";
    
    const now = new Date();
    const dataTime = new Date(selectedMachineStatus.timestamp_utc);
    const timeDiff = now.getTime() - dataTime.getTime();
    const maxDelay = 3 * selectedMachineStatus.update_interval_ms;
    
    if (timeDiff > maxDelay) {
      return "unstable";
    } else {
      return "connected";
    }
  };

  const connectionStatus = getConnectionStatus();

  return (
    <main style={{
      background:"linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)", 
      minHeight:"100vh", 
      color:"#e5e7eb", 
      padding:"40px min(80px, 5vw)",
      fontFamily:"ui-sans-serif",
      overflowX:"hidden"
    }}>
      {/* Container responsivo - adapta de 1200px a 1760px */}
      <div style={{maxWidth:"min(1760px, 95vw)", margin:"0 auto", width:"100%"}}>
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
              CNC-Genius Telemetria
            </h1>
            <p style={{fontSize:14, opacity:0.6, margin:0}}>
              Monitoramento em tempo real • Atualização a cada 1s
            </p>
          </div>
          <div style={{display:"flex", gap:16, alignItems:"center"}}>
            {/* Connection Status Badge */}
            <div style={{
              background: connectionStatus === "connected" ? "rgba(16, 185, 129, 0.1)" : 
                         connectionStatus === "unstable" ? "rgba(245, 158, 11, 0.1)" : "rgba(239, 68, 68, 0.1)",
              border: `1px solid ${connectionStatus === "connected" ? "rgba(16, 185, 129, 0.3)" : 
                                  connectionStatus === "unstable" ? "rgba(245, 158, 11, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
              padding:"8px 16px",
              borderRadius:8,
              fontSize:12,
              color: connectionStatus === "connected" ? "#10b981" : 
                     connectionStatus === "unstable" ? "#f59e0b" : "#ef4444"
            }}>
              {connectionStatus === "connected" ? "Conectado" : 
               connectionStatus === "unstable" ? "Sinal instável" : "Sem atualização"}
            </div>
            
            {/* Machine Badge */}
            <div style={{
              background:"rgba(59, 130, 246, 0.1)",
              border:"1px solid rgba(59, 130, 246, 0.3)",
              padding:"12px 24px",
              borderRadius:12,
              textAlign:"right"
            }}>
              <div style={{fontSize:12, opacity:0.7, marginBottom:4}}>Máquina</div>
              <div style={{fontSize:18, fontWeight:600, color:"#3b82f6"}}>
                {selectedMachineStatus?.machine_id || "—"}
              </div>
            </div>
          </div>
        </header>

      {/* Machine Selector */}
      <ErrorBoundary fallback={<NetworkErrorFallback />}>
        <MachineSelector />
      </ErrorBoundary>

      {/* Navigation Tabs */}
      <div style={{
        display: "flex",
        gap: "4px",
        marginBottom: "20px",
        borderBottom: "2px solid #e5e7eb"
      }}>
        <button
          onClick={() => setActiveTab('dashboard')}
          style={{
            padding: "12px 24px",
            border: "none",
            background: activeTab === 'dashboard' ? "#3b82f6" : "transparent",
            color: activeTab === 'dashboard' ? "white" : "#6b7280",
            borderRadius: "8px 8px 0 0",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "500"
          }}
        >
          📊 Dashboard
        </button>
        <button
          onClick={() => setActiveTab('health')}
          style={{
            padding: "12px 24px",
            border: "none",
            background: activeTab === 'health' ? "#3b82f6" : "transparent",
            color: activeTab === 'health' ? "white" : "#6b7280",
            borderRadius: "8px 8px 0 0",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "500"
          }}
        >
          🏥 Diagnóstico do Box
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'health' ? (
        <ErrorBoundary fallback={<DataErrorFallback />}>
          <BoxHealth />
        </ErrorBoundary>
      ) : (
        <ErrorBoundary onError={handleError}>

      {machinesError && (
        <div style={{background:"rgba(220,38,38,0.2)", border:"1px solid #dc2626", borderRadius:8, padding:16, marginBottom:16}}>
          <strong>Erro:</strong> {machinesError}
        </div>
      )}

      {selectedMachineError && (
        <div style={{background:"rgba(220,38,38,0.2)", border:"1px solid #dc2626", borderRadius:8, padding:16, marginBottom:16}}>
          <strong>Erro na máquina:</strong> {selectedMachineError}
        </div>
      )}

      {selectedMachineLoading && !selectedMachineStatus && (
        <div style={{textAlign:"center", padding:32, opacity:0.5}}>
          Carregando status da máquina...
        </div>
      )}

      {/* Machine State Card - Visão geral para o piloto Nestor */}
      <section style={{marginBottom:32}}>
        <ErrorBoundary fallback={<DataErrorFallback />}>
          <MachineStateCard />
        </ErrorBoundary>
      </section>

      {/* Top Row - 3 Large Cards */}
      <section style={{
        display:"grid", 
        gridTemplateColumns:"repeat(3, 1fr)", 
        gap:24, 
        marginBottom:24
      }}>
        <Card 
          title="RPM" 
          value={selectedMachineStatus?.rpm?.toFixed(1) ?? "—"} 
          suffix="rev/min"
          color={getExecutionColor(selectedMachineStatus?.execution)}
          large={true}
        />
        <Card 
          title="FEED" 
          value={selectedMachineStatus?.feed_rate?.toFixed(1) ?? "—"} 
          suffix="mm/min"
          large={true}
        />
        <Card 
          title="ESTADO" 
          value={formatExecution(selectedMachineStatus?.execution)}
          color={getExecutionColor(selectedMachineStatus?.execution)}
          large={true}
        />
      </section>

      {/* Bottom Row - 4 Smaller Cards */}
      <section style={{
        display:"grid", 
        gridTemplateColumns:"repeat(4, 1fr)", 
        gap:24, 
        marginBottom:32
      }}>
        <Card 
          title="MODO" 
          value={formatMode(selectedMachineStatus?.mode)}
        />
        <Card 
          title="LOAD (%)" 
          value={selectedMachineStatus?.spindle_load_pct?.toFixed(0) ?? "—"}
          suffix={selectedMachineStatus?.spindle_load_pct ? "%" : undefined}
        />
        <Card 
          title="FERRAMENTA" 
          value={selectedMachineStatus?.tool_id ?? "—"}
        />
        <AlarmCard 
          alarmCode={selectedMachineStatus?.alarm_code}
          alarmMessage={selectedMachineStatus?.alarm_message}
        />
      </section>

      {/* Log de Eventos v0.2 */}
      <section style={{marginBottom:32}}>
        <h2 style={{
          fontSize:24, 
          fontWeight:700, 
          marginBottom:16, 
          color:"#e5e7eb"
        }}>
          Log de eventos recentes
        </h2>
        
        {eventsError && (
          <div style={{
            background:"rgba(245, 158, 11, 0.2)", 
            border:"1px solid #f59e0b", 
            borderRadius:8, 
            padding:12, 
            marginBottom:16,
            fontSize:14
          }}>
            {eventsError}
          </div>
        )}
        
        <div style={{
          background:"linear-gradient(135deg, #1f2937 0%, #111827 100%)",
          borderRadius:16,
          border:"1px solid #374151",
          overflow:"hidden"
        }}>
          {events.length === 0 ? (
            <div style={{
              padding:32,
              textAlign:"center",
              opacity:0.6,
              fontSize:14
            }}>
              {eventsError ? "Erro ao carregar eventos" : "Nenhum evento recente"}
            </div>
          ) : (
            <div style={{overflowX:"auto"}}>
              <table style={{
                width:"100%",
                borderCollapse:"collapse"
              }}>
                <thead>
                  <tr style={{
                    background:"rgba(0,0,0,0.3)",
                    borderBottom:"1px solid #374151"
                  }}>
                    <th style={{padding:"12px 16px", textAlign:"left", fontSize:12, fontWeight:600, opacity:0.8}}>Horário</th>
                    <th style={{padding:"12px 16px", textAlign:"left", fontSize:12, fontWeight:600, opacity:0.8}}>Estado</th>
                    <th style={{padding:"12px 16px", textAlign:"left", fontSize:12, fontWeight:600, opacity:0.8}}>RPM</th>
                    <th style={{padding:"12px 16px", textAlign:"left", fontSize:12, fontWeight:600, opacity:0.8}}>Feed</th>
                    <th style={{padding:"12px 16px", textAlign:"left", fontSize:12, fontWeight:600, opacity:0.8}}>Alarme</th>
                  </tr>
                </thead>
                <tbody>
                  {events.slice(0, 10).map((event, index) => (
                    <tr key={index} style={{
                      borderBottom: index < 9 ? "1px solid rgba(55, 65, 81, 0.5)" : "none"
                    }}>
                      <td style={{padding:"12px 16px", fontSize:13}}>
                        {formatTime(event.timestamp_utc)}
                      </td>
                      <td style={{padding:"12px 16px", fontSize:13}}>
                        <span style={{
                          color: getExecutionColor(event.execution),
                          fontWeight:600
                        }}>
                          {formatExecution(event.execution)}
                        </span>
                      </td>
                      <td style={{padding:"12px 16px", fontSize:13}}>
                        {event.rpm.toFixed(0)}
                      </td>
                      <td style={{padding:"12px 16px", fontSize:13}}>
                        {event.feed_rate?.toFixed(0) ?? "—"}
                      </td>
                      <td style={{padding:"12px 16px", fontSize:13}}>
                        {event.alarm_code ? (
                          <span style={{color:"#ef4444"}}>
                            {event.alarm_code}
                            {event.alarm_message && ` - ${event.alarm_message.substring(0, 30)}${event.alarm_message.length > 30 ? '...' : ''}`}
                          </span>
                        ) : (
                          <span style={{opacity:0.5}}>—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* OEE Card - Full Width */}
      <section style={{marginBottom:32}}>
        <ErrorBoundary fallback={<DataErrorFallback />}>
          <OEECard machineId={selectedMachineId || ""} />
        </ErrorBoundary>
      </section>

        </>
        )}
      </ErrorBoundary>

      {/* Footer */}
      <footer style={{
        marginTop:40, 
        paddingTop:24,
        borderTop:"1px solid rgba(255,255,255,0.05)",
        fontSize:12, 
        opacity:0.5, 
        textAlign:"center"
      }}>
        <div>Polling: 2s (máquinas) | 1s (status) | Eventos: {EVENTS_POLL_INTERVAL_MS / 1000}s | API: {import.meta.env.VITE_API_BASE || 'http://localhost:8001'}</div>
        <div style={{marginTop:8}}>CNC-Genius Telemetria v0.2 • Dashboard + Log de eventos • 1920×1080</div>
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
  large?: boolean;
}

function Card({ title, value, suffix, color, large }: CardProps) {
  return (
    <div style={{
      background:"linear-gradient(135deg, #1f2937 0%, #111827 100%)", 
      padding: large ? "36px 32px" : "24px 20px", 
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
        fontSize: large ? 48 : 36, 
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

// AlarmCard component for wider alarm display
function AlarmCard({ alarmCode, alarmMessage }: { alarmCode?: string | null, alarmMessage?: string | null }) {
  const hasAlarm = alarmCode || alarmMessage;
  
  return (
    <div style={{
      background:"linear-gradient(135deg, #1f2937 0%, #111827 100%)", 
      padding:"24px 20px", 
      borderRadius:20, 
      border:"1px solid #374151",
      boxShadow:"0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
      transition:"all 0.3s ease",
      position:"relative" as const,
      overflow:"hidden",
      gridColumn: "span 1" // Takes full width in 4-column grid
    }}>
      <div style={{
        fontSize:13, 
        opacity:0.7, 
        marginBottom:12, 
        textTransform:"uppercase", 
        letterSpacing:"0.08em",
        fontWeight:600,
        position:"relative" as const
      }}>
        ALARME
      </div>
      
      {hasAlarm ? (
        <div>
          <div style={{
            fontSize:24, 
            fontWeight:700, 
            color: "#ef4444",
            lineHeight:1,
            marginBottom:8,
            position:"relative" as const
          }}>
            {alarmCode ? `${alarmCode}` : "ATIVO"}
          </div>
          {alarmMessage && (
            <div style={{
              fontSize:12, 
              opacity:0.8, 
              color: "#ef4444",
              position:"relative" as const,
              lineHeight:1.3
            }}>
              {alarmMessage}
            </div>
          )}
        </div>
      ) : (
        <div style={{
          fontSize:24, 
          fontWeight:700, 
          color: "#10b981",
          lineHeight:1,
          marginBottom:8,
          position:"relative" as const
        }}>
          Nenhum
        </div>
      )}
    </div>
  );
}

// Wrap AppContent with MachinesProvider
export default function App() {
  return (
    <MachinesProvider>
      <AppContent />
    </MachinesProvider>
  );
}

function formatExecution(execution?: string): string {
  if (!execution) return "—";
  switch (execution) {
    case "EXECUTING":
      return "RODANDO";
    case "STOPPED":
      return "PARADA";
    case "READY":
      return "PRONTA";
    default:
      return execution;
  }
}

function getExecutionColor(execution?: string): string {
  switch (execution) {
    case "EXECUTING":
      return "#10b981"; // green
    case "STOPPED":
      return "#ef4444"; // red
    case "READY":
      return "#f59e0b"; // yellow
    default:
      return "#e5e7eb"; // gray
  }
}

function formatMode(mode?: string): string {
  if (!mode) return "—";
  switch (mode) {
    case "AUTOMATIC":
      return "AUTO";
    case "MANUAL":
      return "MANUAL";
    default:
      return mode;
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

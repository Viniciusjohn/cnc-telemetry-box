import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE || "http://localhost:8001";
const MID = "ABR-850";

type Status = {
  machine_id: string;
  rpm: number;
  feed_mm_min: number;
  running: boolean;
  stopped: boolean;
  last_update: string;
  session: { machining_time_sec: number; stopped_time_sec: number; };
};

export default function App() {
  const [data, setData] = useState<Status | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const tick = async () => {
      try {
        const res = await fetch(`${API}/v1/machines/${MID}/status`, {
          headers: {
            "X-Request-Id": crypto.randomUUID(),
            "X-Contract-Fingerprint": "010191590cf1"
          }
        });
        const j = await res.json();
        setData(j);
        setErr(null);
      } catch (e:any) {
        setErr(e?.message || "fetch failed");
      }
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{background:"#0a0a0a", minHeight:"100vh", color:"#e5e7eb", padding:"24px", fontFamily:"ui-sans-serif"}}>
      <h1 style={{marginBottom:12}}>CNC Telemetria — {MID}</h1>
      {err && <div style={{color:"#f87171"}}>Erro: {err}</div>}
      <div style={{display:"grid", gridTemplateColumns:"repeat(2, minmax(0, 1fr))", gap:"12px", maxWidth:600}}>
        <Card title="RPM" value={data?.rpm ?? "—"} />
        <Card title="Feed (mm/min)" value={data?.feed_mm_min ?? "—"} />
        <Card title="Status" value={data?.running ? "RODANDO" : "PARADA"} />
        <Card title="Tempo usinagem (s)" value={data?.session?.machining_time_sec ?? "—"} />
      </div>
      <small style={{opacity:.7}}>Última atualização: {data?.last_update || "—"}</small>
    </div>
  );
}

function Card({title, value}:{title:string; value:any}) {
  return (
    <div style={{background:"#111827", padding:"16px", borderRadius:"16px", boxShadow:"0 0 0 1px #1f2937 inset"}}>
      <div style={{opacity:.8, fontSize:12}}>{title}</div>
      <div style={{fontSize:28, fontWeight:700, marginTop:4}}>{String(value)}</div>
    </div>
  );
}

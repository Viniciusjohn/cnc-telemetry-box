import React, { useState, useEffect } from 'react';
import './MachineStateCard.css';

interface MachineStateCount {
  running: number;
  idle: number;
  offline: number;
}

interface BoxHealth {
  machine_count_by_state: MachineStateCount;
}

export function MachineStateCard() {
  const [machineStates, setMachineStates] = useState<MachineStateCount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMachineStates = async () => {
      try {
        const response = await fetch('/box/healthz');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data: BoxHealth = await response.json();
        setMachineStates(data.machine_count_by_state);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro desconhecido');
      } finally {
        setLoading(false);
      }
    };

    // Buscar imediatamente
    fetchMachineStates();

    // Atualizar a cada 30 segundos (alinhado com BoxHealth)
    const interval = setInterval(fetchMachineStates, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="machine-state-card">
        <h3>🏭 Estados das Máquinas</h3>
        <div className="loading">Carregando estados...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="machine-state-card">
        <h3>🏭 Estados das Máquinas</h3>
        <div className="error">
          ❌ Erro ao obter estados: {error}
        </div>
      </div>
    );
  }

  if (!machineStates) {
    return null;
  }

  const totalMachines = machineStates.running + machineStates.idle + machineStates.offline;

  const getStateInfo = (state: keyof MachineStateCount) => {
    switch (state) {
      case 'running':
        return {
          label: 'Rodando',
          color: '#22c55e',
          bgColor: '#dcfce7',
          icon: '🟢'
        };
      case 'idle':
        return {
          label: 'Ocioso',
          color: '#f59e0b',
          bgColor: '#fef3c7',
          icon: '🟡'
        };
      case 'offline':
        return {
          label: 'Offline',
          color: '#ef4444',
          bgColor: '#fee2e2',
          icon: '🔴'
        };
    }
  };

  return (
    <div className="machine-state-card">
      <div className="card-header">
        <h3>🏭 Estados das Máquinas</h3>
        <div className="total-machines">
          Total: <strong>{totalMachines}</strong>
        </div>
      </div>

      <div className="states-grid">
        {Object.entries(machineStates).map(([state, count]) => {
          const stateInfo = getStateInfo(state as keyof MachineStateCount);
          const percentage = totalMachines > 0 ? (count / totalMachines) * 100 : 0;
          
          return (
            <div 
              key={state} 
              className="state-item"
              style={{ 
                borderLeft: `4px solid ${stateInfo.color}`,
                backgroundColor: stateInfo.bgColor
              }}
            >
              <div className="state-header">
                <span className="state-icon">{stateInfo.icon}</span>
                <span className="state-label">{stateInfo.label}</span>
                <span className="state-count">{count}</span>
              </div>
              
              <div className="state-percentage">
                {percentage.toFixed(1)}%
              </div>
              
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ 
                    width: `${percentage}%`,
                    backgroundColor: stateInfo.color
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="card-footer">
        <small>
          📊 Baseado em heartbeat das máquinas • Atualizado a cada 30s
        </small>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import './BoxHealth.css';

interface ServiceStatus {
  database: string;
  backend: string;
  adapter: string;
  sync: string;
  frontend: string;
}

interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  uptime_seconds: number;
}

interface BoxHealth {
  status: 'healthy' | 'degraded';
  version: string;
  timestamp: string;
  services: ServiceStatus;
  system: SystemMetrics;
  alerts: string[];
  uptime_formatted: string;
}

export function BoxHealth() {
  const [health, setHealth] = useState<BoxHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch('/box/healthz');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        setHealth(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro desconhecido');
      } finally {
        setLoading(false);
      }
    };

    // Buscar imediatamente
    fetchHealth();

    // Atualizar a cada 30 segundos
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="box-health">
        <h2>🏥 CNC Telemetry Box - Diagnóstico</h2>
        <div className="loading">Carregando informações do Box...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="box-health">
        <h2>🏥 CNC Telemetry Box - Diagnóstico</h2>
        <div className="error">
          ❌ Erro ao obter informações: {error}
        </div>
      </div>
    );
  }

  if (!health) {
    return null;
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return '✅';
      case 'error':
        return '❌';
      default:
        return '⚠️';
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'running':
        return 'status-running';
      case 'error':
        return 'status-error';
      default:
        return 'status-warning';
    }
  };

  const getProgressBarClass = (percent: number) => {
    if (percent < 60) return 'progress-good';
    if (percent < 85) return 'progress-warning';
    return 'progress-critical';
  };

  return (
    <div className="box-health">
      <div className="health-header">
        <h2>🏥 CNC Telemetry Box - Diagnóstico</h2>
        <div className={`overall-status status-${health.status}`}>
          {health.status === 'healthy' ? '✅ Saudável' : '⚠️ Degradado'}
        </div>
      </div>

      <div className="health-grid">
        {/* Status Global */}
        <div className="card">
          <h3>📊 Status Geral</h3>
          <div className="status-info">
            <div><strong>Estado:</strong> <span className={`status-${health.status}`}>{health.status}</span></div>
            <div><strong>Versão:</strong> {health.version}</div>
            <div><strong>Uptime:</strong> {health.uptime_formatted}</div>
            <div><strong>Atualizado:</strong> {new Date(health.timestamp).toLocaleString('pt-BR')}</div>
          </div>
        </div>

        {/* Serviços */}
        <div className="card">
          <h3>🔧 Serviços</h3>
          <div className="services-grid">
            {Object.entries(health.services).map(([service, status]) => (
              <div key={service} className={`service-item ${getStatusClass(status)}`}>
                <span className="service-icon">{getStatusIcon(status)}</span>
                <span className="service-name">{service}</span>
                <span className="service-status">{status}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Sistema */}
        <div className="card full-width">
          <h3>💻 Recursos do Sistema</h3>
          <div className="metrics-grid">
            <div className="metric">
              <div className="metric-label">CPU</div>
              <div className="metric-value">{health.system.cpu_percent.toFixed(1)}%</div>
              <div className="progress-bar">
                <div 
                  className={`progress-fill ${getProgressBarClass(health.system.cpu_percent)}`}
                  style={{ width: `${health.system.cpu_percent}%` }}
                />
              </div>
            </div>

            <div className="metric">
              <div className="metric-label">Memória</div>
              <div className="metric-value">
                {health.system.memory_used_gb.toFixed(1)} / {health.system.memory_total_gb.toFixed(1)} GB
              </div>
              <div className="metric-percent">{health.system.memory_percent.toFixed(1)}%</div>
              <div className="progress-bar">
                <div 
                  className={`progress-fill ${getProgressBarClass(health.system.memory_percent)}`}
                  style={{ width: `${health.system.memory_percent}%` }}
                />
              </div>
            </div>

            <div className="metric">
              <div className="metric-label">Disco</div>
              <div className="metric-value">
                {health.system.disk_used_gb.toFixed(1)} / {health.system.disk_total_gb.toFixed(1)} GB
              </div>
              <div className="metric-percent">{health.system.disk_percent.toFixed(1)}%</div>
              <div className="progress-bar">
                <div 
                  className={`progress-fill ${getProgressBarClass(health.system.disk_percent)}`}
                  style={{ width: `${health.system.disk_percent}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Alertas */}
        {health.alerts.length > 0 && (
          <div className="card full-width">
            <h3>⚠️ Alertas</h3>
            <div className="alerts-list">
              {health.alerts.map((alert, index) => (
                <div key={index} className="alert-item">
                  🚨 {alert}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="health-footer">
        <small>
          Atualizado automaticamente a cada 30 segundos • Recarregue para atualizar manualmente
        </small>
      </div>
    </div>
  );
}

import React, { useMemo, useCallback, useState, useEffect } from 'react';
import './OEECard.css';

interface OEEData {
  availability: number;
  performance: number;
  quality: number;
  oee: number;
  lastUpdated: string;
}

interface MemoizedOEECardProps {
  machineId: string;
  className?: string;
}

// Cache para OEE data por machineId
const oeeCache = new Map<string, { data: OEEData | null; timestamp: number; ttl: number }>();

const MemoizedOEECard = React.memo<MemoizedOEECardProps>(({ 
  machineId, 
  className = "" 
}) => {
  const [oeeData, setOeeData] = useState<OEEData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Memoizar função de fetch com cache
  const fetchOEEData = useCallback(async () => {
    if (!machineId) return;

    // Verificar cache
    const cached = oeeCache.get(machineId);
    const now = Date.now();
    
    if (cached && (now - cached.timestamp) < cached.ttl) {
      setOeeData(cached.data);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/v1/machines/${machineId}/oee`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Validar estrutura dos dados
      const validatedData: OEEData = {
        availability: Math.max(0, Math.min(100, data.availability || 0)),
        performance: Math.max(0, Math.min(100, data.performance || 0)),
        quality: Math.max(0, Math.min(100, data.quality || 0)),
        oee: Math.max(0, Math.min(100, data.oee || 0)),
        lastUpdated: data.lastUpdated || new Date().toISOString()
      };

      // Atualizar cache (TTL de 30 segundos)
      oeeCache.set(machineId, {
        data: validatedData,
        timestamp: now,
        ttl: 30000
      });

      setOeeData(validatedData);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setError(errorMessage);
      console.error('Failed to fetch OEE data:', err);
    } finally {
      setLoading(false);
    }
  }, [machineId]);

  // Memoizar cálculo de cores baseado nos valores
  const getMetricColor = useCallback((value: number): { bg: string; text: string } => {
    if (value >= 85) return { bg: '#dcfce7', text: '#166534' }; // green
    if (value >= 70) return { bg: '#fef3c7', text: '#92400e' }; // yellow
    return { bg: '#fee2e2', text: '#991b1b' }; // red
  }, []);

  // Memoizar dados formatados
  const formattedData = useMemo(() => {
    if (!oeeData) return null;

    return {
      availability: {
        value: oeeData.availability,
        display: oeeData.availability.toFixed(1),
        color: getMetricColor(oeeData.availability)
      },
      performance: {
        value: oeeData.performance,
        display: oeeData.performance.toFixed(1),
        color: getMetricColor(oeeData.performance)
      },
      quality: {
        value: oeeData.quality,
        display: oeeData.quality.toFixed(1),
        color: getMetricColor(oeeData.quality)
      },
      oee: {
        value: oeeData.oee,
        display: oeeData.oee.toFixed(1),
        color: getMetricColor(oeeData.oee)
      },
      lastUpdated: new Date(oeeData.lastUpdated).toLocaleString('pt-BR')
    };
  }, [oeeData, getMetricColor]);

  // Memoizar componente de métrica
  const MetricCard = React.memo<{
    title: string;
    value: string;
    subtitle: string;
    color: { bg: string; text: string };
  }>(({ title, value, subtitle, color }) => (
    <div 
      className="metric-card"
      style={{ backgroundColor: color.bg, color: color.text }}
    >
      <div className="metric-title">{title}</div>
      <div className="metric-value">{value}%</div>
      <div className="metric-subtitle">{subtitle}</div>
    </div>
  ));

  // Effect para buscar dados quando machineId mudar
  useEffect(() => {
    fetchOEEData();
    
    // Configurar polling (a cada 30 segundos)
    const interval = setInterval(fetchOEEData, 30000);
    
    return () => clearInterval(interval);
  }, [fetchOEEData]);

  // Loading state
  if (loading) {
    return (
      <div className={`oee-card loading ${className}`}>
        <div className="oee-header">
          <h3>📈 OEE - {machineId}</h3>
        </div>
        <div className="oee-metrics">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="metric-card skeleton">
              <div className="skeleton-title"></div>
              <div className="skeleton-value"></div>
              <div className="skeleton-subtitle"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`oee-card error ${className}`}>
        <div className="oee-header">
          <h3>📈 OEE - {machineId}</h3>
        </div>
        <div className="error-content">
          <span className="error-icon">⚠️</span>
          <p>Erro ao carregar dados OEE</p>
          <small>{error}</small>
          <button onClick={fetchOEEData} className="retry-button">
            🔄 Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  // No data state
  if (!formattedData) {
    return (
      <div className={`oee-card no-data ${className}`}>
        <div className="oee-header">
          <h3>📈 OEE - {machineId}</h3>
        </div>
        <div className="no-data-content">
          <span className="no-data-icon">📊</span>
          <p>Dados OEE não disponíveis</p>
          <small>Aguardando telemetria da máquina...</small>
        </div>
      </div>
    );
  }

  return (
    <div className={`oee-card ${className}`}>
      <div className="oee-header">
        <h3>📈 OEE - {machineId}</h3>
        <div className="last-updated">
          <small>Atualizado: {formattedData.lastUpdated}</small>
        </div>
      </div>
      
      <div className="oee-metrics">
        <MetricCard
          title="Disponibilidade"
          value={formattedData.availability.display}
          subtitle="Tempo de operação"
          color={formattedData.availability.color}
        />
        
        <MetricCard
          title="Performance"
          value={formattedData.performance.display}
          subtitle="Velocidade vs padrão"
          color={formattedData.performance.color}
        />
        
        <MetricCard
          title="Qualidade"
          value={formattedData.quality.display}
          subtitle="Peças boas / total"
          color={formattedData.quality.color}
        />
        
        <MetricCard
          title="OEE Total"
          value={formattedData.oee.display}
          subtitle="Eficiência geral"
          color={formattedData.oee.color}
        />
      </div>

      <div className="oee-footer">
        <div className="oee-gauge">
          <div 
            className="gauge-fill"
            style={{ 
              width: `${formattedData.oee.value}%`,
              backgroundColor: formattedData.oee.color.text
            }}
          ></div>
        </div>
        <div className="oee-summary">
          <strong>OEE: {formattedData.oee.display}%</strong>
          <span>
            {formattedData.oee.value >= 85 ? '🟢 Excelente' :
             formattedData.oee.value >= 70 ? '🟡 Bom' :
             '🔴 Precisa melhorar'}
          </span>
        </div>
      </div>
    </div>
  );
});

MemoizedOEECard.displayName = 'MemoizedOEECard';

export default MemoizedOEECard;

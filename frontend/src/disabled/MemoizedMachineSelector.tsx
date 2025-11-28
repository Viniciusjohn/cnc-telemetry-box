import React, { useMemo, useCallback } from 'react';
import { useMachines } from '../contexts/MachinesContext';
import './MachineSelector.css';

interface MachineOption {
  value: string;
  label: string;
  status: 'running' | 'stopped' | 'idle';
  rpm: number;
}

interface MemoizedMachineSelectorProps {
  onMachineChange?: (machineId: string) => void;
  className?: string;
}

const MemoizedMachineSelector = React.memo<MemoizedMachineSelectorProps>(({ 
  onMachineChange, 
  className = "" 
}) => {
  const { 
    machines, 
    selectedMachineId, 
    setSelectedMachineId,
    machinesLoading,
    machinesError 
  } = useMachines();

  // Memoizar opções de máquinas para evitar re-render desnecessário
  const machineOptions = useMemo(() => {
    if (!machines || machines.length === 0) {
      return [];
    }

    return machines.map(machine => ({
      value: machine.machine_id,
      label: machine.machine_id,
      status: machine.state as 'running' | 'stopped' | 'idle',
      rpm: machine.rpm || 0
    }));
  }, [machines]);

  // Memoizar handler de seleção
  const handleSelectionChange = useCallback((event: React.ChangeEvent<HTMLSelectElement>) => {
    const newMachineId = event.target.value;
    setSelectedMachineId(newMachineId);
    onMachineChange?.(newMachineId);
  }, [setSelectedMachineId, onMachineChange]);

  // Memoizar status indicator
  const StatusIndicator = React.memo<{ status: 'running' | 'stopped' | 'idle' }>(({ status }) => {
    const statusConfig = useMemo(() => ({
      running: { color: '#10b981', label: 'Rodando', icon: '🟢' },
      stopped: { color: '#ef4444', label: 'Parada', icon: '🔴' },
      idle: { color: '#f59e0b', label: 'Ociosa', icon: '🟡' }
    }), []);

    const config = statusConfig[status];
    
    return (
      <span 
        className="status-indicator"
        style={{ color: config.color }}
        title={config.label}
      >
        {config.icon}
      </span>
    );
  });

  // Memoizar renderização da opção
  const renderOption = useCallback((option: MachineOption) => (
    <option key={option.value} value={option.value}>
      {option.label} - {option.status} ({option.rpm} RPM)
    </option>
  ), []);

  // Loading state
  if (machinesLoading) {
    return (
      <div className={`machine-selector loading ${className}`}>
        <div className="selector-header">
          <span>🏭 Máquinas</span>
        </div>
        <select disabled className="machine-select">
          <option>Carregando...</option>
        </select>
      </div>
    );
  }

  // Error state
  if (machinesError) {
    return (
      <div className={`machine-selector error ${className}`}>
        <div className="selector-header">
          <span>🏭 Máquinas</span>
        </div>
        <select disabled className="machine-select">
          <option>Erro ao carregar</option>
        </select>
        <div className="error-message">
          <small>{machinesError}</small>
        </div>
      </div>
    );
  }

  // No machines state
  if (machineOptions.length === 0) {
    return (
      <div className={`machine-selector empty ${className}`}>
        <div className="selector-header">
          <span>🏭 Máquinas</span>
        </div>
        <select disabled className="machine-select">
          <option>Nenhuma máquina encontrada</option>
        </select>
      </div>
    );
  }

  // Normal state
  const selectedOption = machineOptions.find(opt => opt.value === selectedMachineId);

  return (
    <div className={`machine-selector ${className}`}>
      <div className="selector-header">
        <span>🏭 Máquinas</span>
        {selectedOption && (
          <StatusIndicator status={selectedOption.status} />
        )}
      </div>
      
      <select 
        value={selectedMachineId || ''}
        onChange={handleSelectionChange}
        className="machine-select"
        aria-label="Selecione uma máquina"
      >
        <option value="">Selecione uma máquina...</option>
        {machineOptions.map(renderOption)}
      </select>

      {selectedOption && (
        <div className="selected-info">
          <div className="info-row">
            <span>Status:</span>
            <span className={`status-text ${selectedOption.status}`}>
              {selectedOption.status}
            </span>
          </div>
          <div className="info-row">
            <span>RPM:</span>
            <span className="rpm-value">{selectedOption.rpm.toLocaleString('pt-BR')}</span>
          </div>
        </div>
      )}
    </div>
  );
});

// Display name para debugging
MemoizedMachineSelector.displayName = 'MemoizedMachineSelector';

export default MemoizedMachineSelector;

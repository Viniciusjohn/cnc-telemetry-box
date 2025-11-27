import { useMachines } from "../contexts/MachinesContext";

export function MachineSelector() {
  const { 
    machines, 
    machinesGrid, 
    machinesLoading, 
    machinesError,
    selectedMachineId,
    selectMachine 
  } = useMachines();

  const getExecutionColor = (execution: string): string => {
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
  };

  const formatExecution = (execution: string): string => {
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
  };

  if (machinesError) {
    return (
      <div style={{
        background: "rgba(220, 38, 38, 0.1)",
        border: "1px solid rgba(220, 38, 38, 0.3)",
        borderRadius: 8,
        padding: 16,
        marginBottom: 24
      }}>
        <strong>Erro ao carregar máquinas:</strong> {machinesError}
      </div>
    );
  }

  if (machinesLoading && machines.length === 0) {
    return (
      <div style={{
        background: "rgba(59, 130, 246, 0.1)",
        border: "1px solid rgba(59, 130, 246, 0.3)",
        borderRadius: 8,
        padding: 16,
        marginBottom: 24,
        textAlign: "center"
      }}>
        Carregando máquinas...
      </div>
    );
  }

  if (machines.length === 0) {
    return (
      <div style={{
        background: "rgba(245, 158, 11, 0.1)",
        border: "1px solid rgba(245, 158, 11, 0.3)",
        borderRadius: 8,
        padding: 16,
        marginBottom: 24,
        textAlign: "center"
      }}>
        Nenhuma máquina encontrada. Envie telemetria para começar.
      </div>
    );
  }

  return (
    <div style={{
      background: "linear-gradient(135deg, #1f2937 0%, #111827 100%)",
      borderRadius: 16,
      border: "1px solid #374151",
      padding: 20,
      marginBottom: 24
    }}>
      <div style={{
        fontSize: 18,
        fontWeight: 600,
        marginBottom: 16,
        color: "#e5e7eb"
      }}>
        Selecionar Máquina
      </div>
      
      {/* Machine buttons */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: 12,
        marginBottom: 20
      }}>
        {machines.map(machineId => {
          const gridItem = machinesGrid.find(item => item.machine_id === machineId);
          const isSelected = machineId === selectedMachineId;
          
          return (
            <button
              key={machineId}
              onClick={() => selectMachine(machineId)}
              style={{
                background: isSelected 
                  ? "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)"
                  : "linear-gradient(135deg, #374151 0%, #1f2937 100%)",
                border: isSelected 
                  ? "1px solid #3b82f6"
                  : "1px solid #4b5563",
                borderRadius: 12,
                padding: "16px 20px",
                cursor: "pointer",
                transition: "all 0.2s ease",
                textAlign: "left",
                color: isSelected ? "#ffffff" : "#e5e7eb"
              }}
              onMouseEnter={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.background = "linear-gradient(135deg, #4b5563 0%, #374151 100%)";
                  e.currentTarget.style.borderColor = "#6b7280";
                }
              }}
              onMouseLeave={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.background = "linear-gradient(135deg, #374151 0%, #1f2937 100%)";
                  e.currentTarget.style.borderColor = "#4b5563";
                }
              }}
            >
              <div style={{
                fontSize: 16,
                fontWeight: 600,
                marginBottom: 8
              }}>
                {machineId}
              </div>
              
              {gridItem && (
                <div style={{
                  fontSize: 12,
                  opacity: 0.8,
                  display: "flex",
                  alignItems: "center",
                  gap: 8
                }}>
                  <span
                    style={{
                      display: "inline-block",
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: getExecutionColor(gridItem.execution)
                    }}
                  />
                  {formatExecution(gridItem.execution)} • {gridItem.rpm.toFixed(0)} RPM
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Selected machine info */}
      {selectedMachineId && (
        <div style={{
          background: "rgba(59, 130, 246, 0.1)",
          border: "1px solid rgba(59, 130, 246, 0.3)",
          borderRadius: 8,
          padding: 12,
          fontSize: 14,
          color: "#3b82f6"
        }}>
          <strong>Máquina selecionada:</strong> {selectedMachineId}
        </div>
      )}
    </div>
  );
}

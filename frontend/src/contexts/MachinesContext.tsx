import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { fetchMachines, fetchMachineStatus, MachineStatus, ApiError } from "../lib/api";

interface MachinesContextType {
  // Machines list and grid data
  machines: string[];
  machinesLoading: boolean;
  machinesError: string | null;
  
  // Selected machine
  selectedMachineId: string | null;
  selectedMachineStatus: MachineStatus | null;
  selectedMachineLoading: boolean;
  selectedMachineError: string | null;
  
  // Actions
  selectMachine: (machineId: string) => void;
  refreshMachines: () => void;
  refreshSelectedMachine: () => void;
}

const MachinesContext = createContext<MachinesContextType | undefined>(undefined);

interface MachinesProviderProps {
  children: ReactNode;
}

export function MachinesProvider({ children }: MachinesProviderProps) {
  const [machines, setMachines] = useState<string[]>([]);
  const [machinesLoading, setMachinesLoading] = useState(false);
  const [machinesError, setMachinesError] = useState<string | null>(null);
  
  const [selectedMachineId, setSelectedMachineId] = useState<string | null>(null);
  const [selectedMachineStatus, setSelectedMachineStatus] = useState<MachineStatus | null>(null);
  const [selectedMachineLoading, setSelectedMachineLoading] = useState(false);
  const [selectedMachineError, setSelectedMachineError] = useState<string | null>(null);

  // Fetch machines list
  useEffect(() => {
    let isMounted = true;
    
    async function fetchMachinesList() {
      try {
        setMachinesLoading(true);
        setMachinesError(null);
        const machinesList = await fetchMachines();
        if (isMounted) {
          setMachines(machinesList);
        }
      } catch (error) {
        if (isMounted) {
          setMachinesError(error instanceof Error ? error.message : "Failed to fetch machines");
          setMachines([]);
        }
      } finally {
        if (isMounted) {
          setMachinesLoading(false);
        }
      }
    }

    fetchMachinesList();
    
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch selected machine status
  useEffect(() => {
    if (!selectedMachineId) {
      setSelectedMachineStatus(null);
      setSelectedMachineError(null);
      return;
    }

    let isMounted = true;
    
    async function fetchStatus() {
      try {
        setSelectedMachineLoading(true);
        setSelectedMachineError(null);
        const status = await fetchMachineStatus(selectedMachineId ?? undefined);
        if (isMounted) {
          setSelectedMachineStatus(status);
          setSelectedMachineError(null);
          setSelectedMachineLoading(false);
        }
      } catch (e) {
        if (isMounted) {
          if (e instanceof ApiError) {
            setSelectedMachineError(`HTTP ${e.status}: ${e.message}`);
          } else {
            setSelectedMachineError(e instanceof Error ? e.message : "Unknown error");
          }
          setSelectedMachineStatus(null);
          setSelectedMachineLoading(false);
        }
      }
    }

    fetchStatus();
    
    // Poll selected machine status every second
    const interval = setInterval(fetchStatus, 1000);
    
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedMachineId]);

  const selectMachine = (machineId: string) => {
    setSelectedMachineId(machineId);
  };

  const refreshMachines = async () => {
    setMachinesLoading(true);
    try {
      const machinesList = await fetchMachines();
      setMachines(machinesList);
      setMachinesError(null);
    } catch (e) {
      if (e instanceof ApiError) {
        setMachinesError(`HTTP ${e.status}: ${e.message}`);
      } else {
        setMachinesError(e instanceof Error ? e.message : "Unknown error");
      }
    } finally {
      setMachinesLoading(false);
    }
  };

  const refreshSelectedMachine = async () => {
    if (!selectedMachineId) return;
    
    setSelectedMachineLoading(true);
    try {
      const status = await fetchMachineStatus(selectedMachineId ?? undefined);
      setSelectedMachineStatus(status);
      setSelectedMachineError(null);
    } catch (e) {
      if (e instanceof ApiError) {
        setSelectedMachineError(`HTTP ${e.status}: ${e.message}`);
      } else {
        setSelectedMachineError(e instanceof Error ? e.message : "Unknown error");
      }
    } finally {
      setSelectedMachineLoading(false);
    }
  };

  const value: MachinesContextType = {
    // Machines list
    machines,
    machinesLoading,
    machinesError,
    
    // Selected machine
    selectedMachineId,
    selectedMachineStatus,
    selectedMachineLoading,
    selectedMachineError,
    
    // Actions
    selectMachine,
    refreshMachines,
    refreshSelectedMachine,
  };

  return (
    <MachinesContext.Provider value={value}>
      {children}
    </MachinesContext.Provider>
  );
}

export function useMachines() {
  const context = useContext(MachinesContext);
  if (context === undefined) {
    throw new Error("useMachines must be used within a MachinesProvider");
  }
  return context;
}

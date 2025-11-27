import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { fetchMachines, fetchMachinesStatusGrid, MachineGridItem, MachineStatus, fetchMachineStatus, ApiError } from "../lib/api";

interface MachinesContextType {
  // Machines list and grid data
  machines: string[];
  machinesGrid: MachineGridItem[];
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
  // Machines list and grid state
  const [machines, setMachines] = useState<string[]>([]);
  const [machinesGrid, setMachinesGrid] = useState<MachineGridItem[]>([]);
  const [machinesLoading, setMachinesLoading] = useState(true);
  const [machinesError, setMachinesError] = useState<string | null>(null);
  
  // Selected machine state
  const [selectedMachineId, setSelectedMachineId] = useState<string | null>(null);
  const [selectedMachineStatus, setSelectedMachineStatus] = useState<MachineStatus | null>(null);
  const [selectedMachineLoading, setSelectedMachineLoading] = useState(false);
  const [selectedMachineError, setSelectedMachineError] = useState<string | null>(null);

  // Poll machines list and grid every 2 seconds
  useEffect(() => {
    let isMounted = true;
    
    async function pollMachines() {
      try {
        // Fetch both machines list and grid in parallel
        const [machinesList, gridData] = await Promise.all([
          fetchMachines(),
          fetchMachinesStatusGrid()
        ]);
        
        if (isMounted) {
          setMachines(machinesList);
          setMachinesGrid(gridData);
          setMachinesError(null);
          setMachinesLoading(false);
          
          // Auto-select first machine if none selected
          if (!selectedMachineId && machinesList.length > 0) {
            setSelectedMachineId(machinesList[0]);
          }
        }
      } catch (e) {
        if (isMounted) {
          if (e instanceof ApiError) {
            setMachinesError(`HTTP ${e.status}: ${e.message}`);
          } else {
            setMachinesError(e instanceof Error ? e.message : "Unknown error");
          }
          setMachinesLoading(false);
        }
      }
    }

    // Initial fetch
    pollMachines();
    
    // Set up polling
    const interval = setInterval(pollMachines, 2000);
    
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedMachineId]);

  // Fetch selected machine status when selection changes
  useEffect(() => {
    if (!selectedMachineId) {
      setSelectedMachineStatus(null);
      setSelectedMachineError(null);
      setSelectedMachineLoading(false);
      return;
    }

    let isMounted = true;
    setSelectedMachineLoading(true);
    setSelectedMachineError(null);

    async function fetchSelectedStatus() {
      try {
        const status = await fetchMachineStatus(selectedMachineId);
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

    fetchSelectedStatus();
    
    // Poll selected machine status every second
    const interval = setInterval(fetchSelectedStatus, 1000);
    
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
      const [machinesList, gridData] = await Promise.all([
        fetchMachines(),
        fetchMachinesStatusGrid()
      ]);
      setMachines(machinesList);
      setMachinesGrid(gridData);
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
      const status = await fetchMachineStatus(selectedMachineId);
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
    // Machines list and grid
    machines,
    machinesGrid,
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

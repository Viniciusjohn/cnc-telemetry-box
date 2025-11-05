/**
 * API client para backend cnc-telemetry.
 * Usa VITE_API_BASE env var (apenas prefixadas são expostas).
 */

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8001";

export interface MachineStatus {
  machine_id: string;
  rpm: number;
  feed_mm_min: number;
  state: "running" | "stopped" | "idle";
  updated_at: string; // ISO 8601
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Busca status de uma máquina.
 * @throws {ApiError} Se response não for ok
 */
export async function fetchMachineStatus(machineId: string): Promise<MachineStatus> {
  const url = `${API_BASE}/v1/machines/${machineId}/status`;
  
  const response = await fetch(url, {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });
  
  if (!response.ok) {
    throw new ApiError(response.status, `Failed to fetch status: ${response.statusText}`);
  }
  
  return response.json();
}

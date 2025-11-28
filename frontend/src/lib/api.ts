/**
 * API client para backend cnc-telemetry.
 * Usa VITE_API_BASE env var (apenas prefixadas são expostas).
 */

import { MACHINE_ID } from "../config/machine";

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export interface MachineStatus {
  machine_id: string;
  controller_family: string;
  timestamp_utc: string;
  mode: string;
  execution: string;
  rpm: number;
  feed_rate: number | null;
  spindle_load_pct: number | null;
  tool_id: string | null;
  alarm_code: string | null;
  alarm_message: string | null;
  part_count: number | null;
  update_interval_ms: number;
  source: string;
}

export interface MachineEvent {
  timestamp_utc: string;
  execution: string;
  mode: string | null;
  rpm: number;
  feed_rate: number | null;
  spindle_load_pct: number | null;
  tool_id: string | null;
  alarm_code: string | null;
  alarm_message: string | null;
  part_count: number | null;
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
export async function fetchMachineStatus(machineId: string = MACHINE_ID): Promise<MachineStatus> {
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

/**
 * Busca eventos históricos de uma máquina.
 * @throws {ApiError} Se response não for ok
 */
export async function fetchMachineEvents(machineId: string = MACHINE_ID, limit: number = 20): Promise<MachineEvent[]> {
  const url = `${API_BASE}/v1/machines/${machineId}/events?limit=${limit}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new ApiError(response.status, `Failed to fetch machine events: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchMachines(): Promise<string[]> {
  const url = `${API_BASE}/v1/machines`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new ApiError(response.status, `Failed to fetch machines list: ${response.statusText}`);
  }

  return response.json();
}

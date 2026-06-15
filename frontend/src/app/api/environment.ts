import { apiGet } from "./client";

export type EnvironmentObservation = {
  region: string;
  city: string;
  temperature_c?: number;
  humidity_percent?: number;
  aqi?: number;
  pm25?: number;
  pm10?: number;
  monsoon_intensity?: string;
};

export type EnvironmentCurrentResponse = {
  observation: EnvironmentObservation | null;
};

export async function getCurrentEnvironment(region = "Delhi", city = "New Delhi"): Promise<EnvironmentCurrentResponse> {
  const params = new URLSearchParams({ region, city });
  return apiGet<EnvironmentCurrentResponse>(`/v1/environment/current?${params.toString()}`);
}

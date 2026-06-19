export interface ChatDeviceOption {
  id: string;
  name: string;
  model: string;
}

export interface DeviceCareSummary {
  self_care_count: number;
  self_as_count: number;
  total_care_count?: number;
  recent_title?: string;
  recent_date?: string;
}

export interface DeviceCareHistoryItem {
  id: string;
  type: "Self Care" | "Self A/S" | string;
  title: string;
  date: string;
}

export interface DeviceDetailOption extends ChatDeviceOption {
  care_summary?: DeviceCareSummary;
  recent_history?: DeviceCareHistoryItem[];
}

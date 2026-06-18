import type { ChatDeviceOption } from "../types/device";

export function getRegisteredDevices(): ChatDeviceOption[] {
  return [
    { id: "1", name: "Living Room Air Conditioner", model: "LG Whisen Wall-mounted" },
    { id: "2", name: "Bedroom Air Conditioner", model: "LG Whisen Wall-mounted" },
  ];
}


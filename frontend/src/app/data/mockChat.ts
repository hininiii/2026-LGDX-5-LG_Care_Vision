import type { Message, ScheduleDateOption } from "../types/chat";

export const PRODUCTS = ["Air Conditioner", "Refrigerator", "Washing Machine", "Air Purifier"];

export const PRODUCT_TYPES: Record<string, string[]> = {
  "Air Conditioner": ["Floor-standing", "Wall-mounted", "Window Type"],
  "Refrigerator": ["Standard", "Side-by-side", "Kimchi Refrigerator"],
  "Washing Machine": ["Front-load", "Top-load"],
  "Air Purifier": ["Floor-standing", "Wall-mounted"],
};

export const PROBLEM_OPTIONS = [
  "Power is unstable or turns off often",
  "Cooling or functions are not working well",
  "The filter has a lot of dust",
  "Noise or vibration is severe",
  "Other issue",
];

export const AVAILABLE_DATES: ScheduleDateOption[] = (() => {
  const dates: ScheduleDateOption[] = [];
  const today = new Date();
  for (let i = 1; i <= 7; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    dates.push({
      label: `${d.getMonth() + 1}/${d.getDate()}(${days[d.getDay()]})`,
      value: d.toLocaleDateString("ko-KR"),
    });
  }
  return dates;
})();

export const TIME_SLOTS = ["09:00~11:00", "11:00~13:00", "14:00~16:00", "16:00~18:00"];

export const initialMessages: Message[] = [
  {
    id: "1",
    type: "bot",
    content: "Hello!\nWelcome to LG Electronics online chat service.\nHow can I help you?",
    time: "12:09 PM",
    options: ["Troubleshoot Product Issue", "Appliance Care Guide", "Connect to Service Center"],
  },
];


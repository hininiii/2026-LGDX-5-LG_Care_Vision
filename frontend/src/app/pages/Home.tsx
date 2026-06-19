import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router";
import { PieChart, Pie, Cell } from "recharts";
import { motion } from "motion/react";
import { Cloud, CloudRain, Sun, Droplets, AirVent, RotateCcw, Tv, Refrigerator } from "lucide-react";
import { evaluateCareRisk, type CareRiskFactor, type CareRiskResponse } from "../api/care";
import { getCurrentEnvironment, type EnvironmentCurrentResponse } from "../api/environment";
import { getUserProfile } from "../api/user";
import acImage from "../../imports/제품페이지관리/47f735f974d0900368394246ff236d4a45df2a58.png";
import careVisionLogo from "../../imports/care-vision-logo.svg";

const HOME_ENVIRONMENT_POLL_INTERVAL_MS = 60 * 60 * 1000;
const SHOW_WELCOME_ONCE_KEY = "careVisionShowWelcomeOnce";

function formatDisplayName(name?: string) {
  const trimmedName = name?.trim();
  if (!trimmedName) return "User";
  return trimmedName.endsWith(" User") ? trimmedName.slice(0, -" User".length) : trimmedName;
}

function displayLocation(region?: string, city?: string) {
  const location = [city, region].filter(Boolean).join(", ");
  return location ? `${location} · Today` : "Updating location · Today";
}

const devices = [
  { id: 1, name: "Air Conditioner", Icon: AirVent, score: 82, climate: 35, usage: 28, care: 19 },
  { id: 2, name: "Washing Machine", Icon: RotateCcw, score: 61, climate: 18, usage: 24, care: 19 },
  { id: 3, name: "TV", Icon: Tv, score: 44, climate: 12, usage: 20, care: 12 },
  { id: 4, name: "Refrigerator", Icon: Refrigerator, score: 31, climate: 8, usage: 14, care: 9 },
];

type CareRiskLevel = CareRiskResponse["care_risk_score"]["risk_level"];

function resolveCareRiskLevel(score: number, riskLevel?: CareRiskLevel) {
  return riskLevel ?? (score >= 85 ? "high" : score >= 65 ? "medium" : "low");
}

function getRiskColor(score: number, riskLevel?: CareRiskLevel) {
  const level = resolveCareRiskLevel(score, riskLevel);
  if (level === "high") return { text: "text-[#FF7A7A]", bar: "bg-[#FF7A7A]", label: "Critical", hex: "#FF7A7A" };
  if (level === "medium") return { text: "text-[#FFE89A]", bar: "bg-[#FFE89A]", label: "Normal", hex: "#FFE89A" };
  return { text: "text-[#45CA9D]", bar: "bg-[#45CA9D]", label: "Good", hex: "#45CA9D" };
}

function getRiskComment(score: number, riskLevel?: CareRiskLevel) {
  const level = resolveCareRiskLevel(score, riskLevel);
  if (level === "high") return "Some devices need care.";
  if (level === "medium") return "Device care status is normal.";
  return "Device care is going well!";
}

function getGaugeScoreColor(score: number, riskLevel?: CareRiskLevel) {
  const level = resolveCareRiskLevel(score, riskLevel);
  if (level === "high") return "#FF7A7A";
  if (level === "medium") return "#FFE89A";
  return "#45CA9D";
}

function sumFactorDelta(factors: CareRiskFactor[], factorNames: string[]) {
  return factors
    .filter((factor) => factorNames.includes(factor.factor))
    .reduce((total, factor) => total + Math.round(factor.score_delta), 0);
}

const triggerReasonPriority: Record<string, number> = {
  humidity_percent: 0,
  aqi: 1,
  particulate_matter: 2,
  rain_monsoon_intensity: 3,
  days_since_last_care: 4,
  daily_runtime_hours: 5,
};

function selectPrimaryTriggerReason(factors: CareRiskFactor[], fallback?: string) {
  if (!factors.length) {
    return fallback ?? "Poor air quality today · We recommend checking the air conditioner filter.";
  }

  const primaryFactor = factors.reduce((selected, candidate) => {
    if (candidate.score_delta !== selected.score_delta) {
      return candidate.score_delta > selected.score_delta ? candidate : selected;
    }

    const selectedPriority = triggerReasonPriority[selected.factor] ?? Number.MAX_SAFE_INTEGER;
    const candidatePriority = triggerReasonPriority[candidate.factor] ?? Number.MAX_SAFE_INTEGER;
    return candidatePriority < selectedPriority ? candidate : selected;
  });

  return primaryFactor.reason || fallback || "Poor air quality today · We recommend checking the air conditioner filter.";
}

const glassCard: React.CSSProperties = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

function TemperatureIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="17"
      height="17"
      viewBox="0 0 17 17"
      fill="none"
      className="flex-shrink-0"
      style={{ width: "16.985px", height: "16.985px" }}
      aria-hidden="true"
    >
      <g clipPath="url(#temperature-icon-clip)">
        <path d="M9.90804 2.83047V10.2898C10.4477 10.6014 10.8695 11.0823 11.108 11.6581C11.3465 12.2338 11.3883 12.8722 11.227 13.4741C11.0657 14.076 10.7103 14.6079 10.2159 14.9873C9.72154 15.3666 9.11578 15.5723 8.49261 15.5723C7.86944 15.5723 7.26368 15.3666 6.76929 14.9873C6.27489 14.6079 5.91949 14.076 5.7582 13.4741C5.59692 12.8722 5.63875 12.2338 5.87723 11.6581C6.11571 11.0823 6.5375 10.6014 7.07718 10.2898V2.83047C7.07718 2.45508 7.2263 2.09506 7.49175 1.82961C7.75719 1.56416 8.11721 1.41504 8.49261 1.41504C8.86801 1.41504 9.22803 1.56416 9.49347 1.82961C9.75892 2.09506 9.90804 2.45508 9.90804 2.83047Z" stroke="#FF694B" strokeWidth="1.41543" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M8.66089 8.35059H9.66089M8.66089 6.35059H9.66089M8.66089 10.3506H9.66089" stroke="#FF694B" strokeLinecap="round" />
      </g>
      <defs>
        <clipPath id="temperature-icon-clip">
          <rect width="16.9852" height="16.9852" fill="white" />
        </clipPath>
      </defs>
    </svg>
  );
}

function AirQualityIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className="flex-shrink-0"
      style={{ width: "15.998px", height: "15.998px" }}
      aria-hidden="true"
    >
      <path d="M8.53219 13.0647C8.70118 13.1915 8.89787 13.2762 9.10605 13.3121C9.31424 13.3479 9.52795 13.3337 9.72958 13.2707C9.93122 13.2077 10.115 13.0977 10.2658 12.9498C10.4166 12.8018 10.53 12.6202 10.5968 12.4198C10.6636 12.2194 10.6818 12.006 10.65 11.7971C10.6181 11.5883 10.5371 11.3901 10.4136 11.2187C10.2901 11.0473 10.1276 10.9078 9.93958 10.8115C9.75154 10.7152 9.54332 10.665 9.33208 10.665H1.33313" stroke="#8D8B8B" strokeWidth="1.33316" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M11.6651 5.3326C11.8355 5.10535 12.0612 4.92544 12.3208 4.80996C12.5803 4.69447 12.865 4.64724 13.1479 4.67275C13.4308 4.69826 13.7025 4.79566 13.9372 4.95571C14.1719 5.11576 14.3617 5.33314 14.4888 5.58721C14.6158 5.84127 14.6758 6.1236 14.663 6.40737C14.6503 6.69114 14.5652 6.96693 14.4158 7.20857C14.2665 7.4502 14.0579 7.64965 13.8098 7.78798C13.5617 7.9263 13.2823 7.99891 12.9983 7.99891H1.33313" stroke="#8D8B8B" strokeWidth="1.33316" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6.53245 2.93265C6.70144 2.8059 6.89813 2.72113 7.10632 2.68532C7.3145 2.6495 7.52821 2.66367 7.72985 2.72666C7.93148 2.78964 8.11526 2.89964 8.26604 3.04759C8.41682 3.19553 8.53029 3.37719 8.59709 3.57759C8.66389 3.77799 8.68211 3.9914 8.65025 4.20023C8.6184 4.40905 8.53737 4.60732 8.41386 4.77869C8.29034 4.95005 8.12787 5.08962 7.93984 5.18588C7.7518 5.28213 7.54358 5.33233 7.33234 5.33233H1.33313" stroke="#8D8B8B" strokeWidth="1.33316" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FineDustIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="19"
      height="20"
      viewBox="0 0 19 20"
      fill="none"
      className="h-[20px] w-[19px] flex-shrink-0"
      style={{ aspectRatio: "19 / 20" }}
      aria-hidden="true"
    >
      <path d="M4.15623 3.75033C4.15623 3.58457 4.09367 3.42559 3.98232 3.30838C3.87097 3.19117 3.71995 3.12533 3.56248 3.12533C3.40501 3.12533 3.25398 3.19117 3.14263 3.30838C3.03129 3.42559 2.96873 3.58457 2.96873 3.75033C2.96873 3.91609 3.03129 4.07506 3.14263 4.19227C3.25398 4.30948 3.40501 4.37533 3.56248 4.37533C3.71995 4.37533 3.87097 4.30948 3.98232 4.19227C4.09367 4.07506 4.15623 3.91609 4.15623 3.75033ZM5.54165 3.75033C5.54165 4.30286 5.33313 4.83276 4.96196 5.22346C4.5908 5.61417 4.08739 5.83366 3.56248 5.83366C3.03757 5.83366 2.53416 5.61417 2.163 5.22346C1.79183 4.83276 1.58331 4.30286 1.58331 3.75033C1.58331 3.19779 1.79183 2.66789 2.163 2.27719C2.53416 1.88649 3.03757 1.66699 3.56248 1.66699C4.08739 1.66699 4.5908 1.88649 4.96196 2.27719C5.33313 2.66789 5.54165 3.19779 5.54165 3.75033ZM9.14373 2.91699C8.39156 2.91703 7.66264 3.19138 7.08097 3.69336C6.4993 4.19534 6.10082 4.89394 5.95331 5.67033C5.92001 5.88351 5.96666 6.10198 6.08344 6.27965C6.20021 6.45733 6.37797 6.58032 6.57923 6.62269C6.78049 6.66506 6.98952 6.6235 7.16223 6.50677C7.33494 6.39004 7.45783 6.20726 7.50498 5.99699C7.58077 5.59829 7.78548 5.23957 8.08427 4.98188C8.38306 4.72419 8.75746 4.58346 9.14373 4.58366H9.30206C9.77448 4.58366 10.2275 4.7812 10.5616 5.13283C10.8956 5.48446 11.0833 5.96138 11.0833 6.45866C11.0833 6.95594 10.8956 7.43285 10.5616 7.78448C10.2275 8.13611 9.77448 8.33366 9.30206 8.33366H2.37498C2.16502 8.33366 1.96365 8.42146 1.81519 8.57774C1.66672 8.73402 1.58331 8.94598 1.58331 9.16699C1.58331 9.38801 1.66672 9.59997 1.81519 9.75625C1.96365 9.91253 2.16502 10.0003 2.37498 10.0003H9.30206C10.1944 10.0003 11.0502 9.62719 11.6812 8.963C12.3122 8.2988 12.6666 7.39797 12.6666 6.45866C12.6666 5.51935 12.3122 4.61851 11.6812 3.95432C11.0502 3.29013 10.1944 2.91699 9.30206 2.91699H9.14373ZM14.8991 7.91699C14.3698 7.91843 13.8543 8.0949 13.4254 8.42148C12.9966 8.74806 12.676 9.20824 12.5091 9.73699C12.4428 9.94673 12.4583 10.1756 12.5523 10.3733C12.6462 10.571 12.811 10.7213 13.0102 10.7912C13.2095 10.861 13.4269 10.8447 13.6147 10.7457C13.8026 10.6468 13.9453 10.4734 14.0117 10.2637C14.1399 9.85783 14.5025 9.58366 14.8999 9.58366C15.4145 9.58366 15.8333 10.0237 15.8333 10.567V10.6253C15.8333 11.2003 15.39 11.667 14.8437 11.667H2.37498C2.16502 11.667 1.96365 11.7548 1.81519 11.9111C1.66672 12.0674 1.58331 12.2793 1.58331 12.5003C1.58331 12.7213 1.66672 12.9333 1.81519 13.0896C1.96365 13.2459 2.16502 13.3337 2.37498 13.3337H11.6771C12.2233 13.3337 12.6666 13.8003 12.6666 14.3753V14.4337C12.6666 14.6945 12.5682 14.9446 12.393 15.129C12.2178 15.3134 11.9802 15.417 11.7325 15.417C11.3359 15.417 10.9733 15.142 10.845 14.737C10.7787 14.5273 10.6359 14.3538 10.4481 14.2549C10.3551 14.2059 10.2538 14.1767 10.1501 14.1689C10.0464 14.1611 9.94222 14.1749 9.84356 14.2095C9.7449 14.2441 9.65368 14.2988 9.5751 14.3705C9.49652 14.4422 9.43213 14.5294 9.38559 14.6273C9.29161 14.825 9.27609 15.0539 9.34244 15.2637C9.50941 15.7925 9.83007 16.2528 10.2591 16.5794C10.6881 16.906 11.2038 17.0824 11.7333 17.0837C12.4008 17.0834 13.0409 16.8041 13.5129 16.3072C13.9849 15.8103 14.25 15.1363 14.25 14.4337V14.3753C14.251 14.0176 14.1837 13.6634 14.0521 13.3337H14.8437C15.1816 13.3337 15.5162 13.2636 15.8283 13.1275C16.1405 12.9914 16.4241 12.7919 16.6631 12.5404C16.902 12.2889 17.0915 11.9903 17.2208 11.6618C17.3501 11.3332 17.4166 10.981 17.4166 10.6253V10.567C17.4166 9.86417 17.1514 9.19013 16.6793 8.69316C16.2072 8.19619 15.5668 7.91699 14.8991 7.91699ZM5.93748 16.8753C5.78001 16.8753 5.62898 16.8095 5.51763 16.6923C5.40629 16.5751 5.34373 16.4161 5.34373 16.2503C5.34373 16.0846 5.40629 15.9256 5.51763 15.8084C5.62898 15.6912 5.78001 15.6253 5.93748 15.6253C6.09495 15.6253 6.24597 15.6912 6.35732 15.8084C6.46867 15.9256 6.53123 16.0846 6.53123 16.2503C6.53123 16.4161 6.46867 16.5751 6.35732 16.6923C6.24597 16.8095 6.09495 16.8753 5.93748 16.8753ZM5.93748 18.3337C6.46239 18.3337 6.9658 18.1142 7.33696 17.7235C7.70813 17.3328 7.91665 16.8029 7.91665 16.2503C7.91665 15.6978 7.70813 15.1679 7.33696 14.7772C6.9658 14.3865 6.46239 14.167 5.93748 14.167C5.41257 14.167 4.90916 14.3865 4.538 14.7772C4.16683 15.1679 3.95831 15.6978 3.95831 16.2503C3.95831 16.8029 4.16683 17.3328 4.538 17.7235C4.90916 18.1142 5.41257 18.3337 5.93748 18.3337ZM16.0312 4.58366C16.0312 4.4179 15.9687 4.25893 15.8573 4.14172C15.746 4.02451 15.595 3.95866 15.4375 3.95866C15.28 3.95866 15.129 4.02451 15.0176 4.14172C14.9063 4.25893 14.8437 4.4179 14.8437 4.58366C14.8437 4.74942 14.9063 4.90839 15.0176 5.0256C15.129 5.14281 15.28 5.20866 15.4375 5.20866C15.595 5.20866 15.746 5.14281 15.8573 5.0256C15.9687 4.90839 16.0312 4.74942 16.0312 4.58366ZM17.4166 4.58366C17.4166 5.13619 17.2081 5.6661 16.837 6.0568C16.4658 6.4475 15.9624 6.66699 15.4375 6.66699C14.9126 6.66699 14.4092 6.4475 14.038 6.0568C13.6668 5.6661 13.4583 5.13619 13.4583 4.58366C13.4583 4.03112 13.6668 3.50122 14.038 3.11052C14.4092 2.71982 14.9126 2.50033 15.4375 2.50033C15.9624 2.50033 16.4658 2.71982 16.837 3.11052C17.2081 3.50122 17.4166 4.03112 17.4166 4.58366Z" fill="#8D8B8B" />
    </svg>
  );
}

function SegmentedGauge({ climate, usage, care, scoreColor = "#FF7A7A" }: { climate: number; usage: number; care: number; scoreColor?: string }) {
  const total = climate + usage + care;
  const totalMax = 105;
  const remaining = totalMax - total;

  const climateRisk = climate; // 35/40 ???꾪뿕???믪쓬
  const usageRisk   = usage;   // 28/40
  const careRisk    = care;    // 19/25

  const pieData = [
    { name: "Care", value: careRisk,    fill: "url(#grad-care)" },
    { name: "Usage", value: usageRisk,   fill: "url(#grad-usage)" },
    { name: "Climate", value: climateRisk, fill: "url(#grad-climate)" },
    { name: "Remaining", value: remaining,   fill: "url(#grad-empty)" },
  ];

  const stats = [
    { label: "Climate", value: climate, color: "#FF7A7A", glow: "rgba(255,122,122,0.22)" },
    { label: "Usage", value: usage,   color: "#FFE89A", glow: "rgba(255,232,154,0.30)" },
    { label: "Care", value: care,    color: "#48D6A6", glow: "rgba(72,214,166,0.22)" },
  ];

  return (
    <div className="flex flex-col items-center w-full">
      {/* 李⑦듃 湲?섏뒪 而⑦뀒?대꼫 */}
      <div className="relative w-full rounded-[20px] flex flex-col items-center pt-[14px] pb-[10px]"
        style={{
          background: "rgba(255,255,255,0.45)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.75)",
          boxShadow: "0 8px 32px rgba(61,220,151,0.08), 0 2px 8px rgba(255,107,104,0.06), inset 0 1px 0 rgba(255,255,255,0.95)",
        }}
      >
        {/* 諛곌꼍 而щ윭 glow */}
        <div className="pointer-events-none absolute bottom-0 left-[10%] w-[35%] h-[50%] rounded-full"
          style={{ background: "rgba(61,220,151,0.12)", filter: "blur(24px)" }} />
        <div className="pointer-events-none absolute bottom-0 left-[35%] w-[30%] h-[50%] rounded-full"
          style={{ background: "rgba(245,158,11,0.10)", filter: "blur(24px)" }} />
        <div className="pointer-events-none absolute bottom-0 right-[10%] w-[35%] h-[50%] rounded-full"
          style={{ background: "rgba(255,107,104,0.12)", filter: "blur(24px)" }} />

        <div className="relative" style={{ width: 220, height: 118 }}>
          <PieChart width={220} height={130}>
            <defs>
              <linearGradient id="grad-climate" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#ffaaaa" />
                <stop offset="100%" stopColor="#FF7A7A" />
              </linearGradient>
              <linearGradient id="grad-usage" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#fff3c0" />
                <stop offset="100%" stopColor="#FFE89A" />
              </linearGradient>
              <linearGradient id="grad-care" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#93ead0" />
                <stop offset="100%" stopColor="#48D6A6" />
              </linearGradient>
              <linearGradient id="grad-empty" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="rgba(220,220,220,0.3)" />
                <stop offset="100%" stopColor="rgba(220,220,220,0.15)" />
              </linearGradient>
            </defs>
            <Pie
              key={total}
              data={pieData}
              cx={110}
              cy={118}
              startAngle={180}
              endAngle={0}
              innerRadius={58}
              outerRadius={100}
              dataKey="value"
              strokeWidth={0}
              paddingAngle={1.5}
            >
              {pieData.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>

          {/* 以묒븰 ?먯닔 */}
          <div className="absolute inset-0 flex items-end justify-center pb-[4px] pointer-events-none">
            <span className="relative inline-flex justify-center" style={{ fontFamily: "Pretendard, sans-serif" }}>
              <span style={{ fontSize: 28, fontWeight: 800, color: scoreColor, lineHeight: 1, minWidth: 42, textAlign: "center" }}>{total}</span>
              <span className="absolute left-full top-[11px]" style={{ fontSize: 13, fontWeight: 600, color: "#aaa", lineHeight: 1 }}>pt</span>
            </span>
          </div>
        </div>
      </div>

      {/* Climate / Usage / Care ?섏튂 ??湲?섏뒪紐⑦뵾利?*/}
      <div className="flex w-full gap-[6px] mt-[6px]">
        {stats.map((s) => (
          <div key={s.label}
            className="flex-1 flex flex-col items-center py-[10px] rounded-[12px]"
            style={{
              background: "rgba(255,255,255,0.55)",
              backdropFilter: "blur(16px)",
              WebkitBackdropFilter: "blur(16px)",
              border: "1px solid rgba(255,255,255,0.75)",
              boxShadow: `0 4px 16px ${s.glow}, inset 0 1px 0 rgba(255,255,255,0.9)`,
            }}
          >
            <span style={{ fontSize: 17, fontWeight: 800, color: s.color, fontFamily: "Pretendard, sans-serif", lineHeight: 1 }}>
              {s.value}
            </span>
            <span style={{ fontSize: 9, fontWeight: 700, color: "#999", fontFamily: "Pretendard, sans-serif", marginTop: 4 }}>{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Home() {
  const navigate = useNavigate();
  const location = useLocation();
  const [aiAlertVisible] = useState(
    (location.state as { aiDismissed?: boolean } | null)?.aiDismissed !== true
  );
  const [showWelcome] = useState(() => localStorage.getItem(SHOW_WELCOME_ONCE_KEY) === "true");
  const [displayName, setDisplayName] = useState("User");
  const [profileLocation, setProfileLocation] = useState<{ region: string; city: string } | null>(null);
  const [careRisk, setCareRisk] = useState<CareRiskResponse | null>(null);
  const [environment, setEnvironment] = useState<EnvironmentCurrentResponse | null>(null);
  const [isCareRiskLoading, setIsCareRiskLoading] = useState(true);
  const [isEnvironmentLoading, setIsEnvironmentLoading] = useState(true);
  const [isAiCareTransitioning, setIsAiCareTransitioning] = useState(false);

  function handleAiCareClick() {
    if (isAiCareTransitioning) return;
    setIsAiCareTransitioning(true);
    window.setTimeout(() => {
      navigate("/self-care");
    }, 240);
  }

  useEffect(() => {
    let active = true;
    let intervalId: number | undefined;

    async function loadHomeData() {
      try {
        const profile = await getUserProfile();
        if (!active) return;
        setDisplayName(formatDisplayName(profile.name));
        const region = profile.region ?? "Delhi";
        const city = profile.city ?? "Delhi";
        setProfileLocation({ region, city });

        setIsCareRiskLoading(true);
        evaluateCareRisk({ region, city, userEmail: profile.user_email ?? profile.email })
          .then((careRiskResponse) => {
            if (active) setCareRisk(careRiskResponse);
          })
          .catch((error) => {
            console.error("Failed to load care risk score", error);
          })
          .finally(() => {
            if (active) setIsCareRiskLoading(false);
          });

        setIsEnvironmentLoading(true);
        getCurrentEnvironment(region, city)
          .then((environmentResponse) => {
            if (active) setEnvironment(environmentResponse);
          })
          .catch((error) => {
            console.error("Failed to load environment data", error);
          })
          .finally(() => {
            if (active) setIsEnvironmentLoading(false);
          });
      } catch (error) {
        console.error("Failed to load home dashboard data", error);
        if (active) {
          setIsCareRiskLoading(false);
          setIsEnvironmentLoading(false);
        }
      }
    }

    loadHomeData();
    intervalId = window.setInterval(loadHomeData, HOME_ENVIRONMENT_POLL_INTERVAL_MS);

    return () => {
      active = false;
      if (intervalId !== undefined) {
        window.clearInterval(intervalId);
      }
    };
  }, []);

  useEffect(() => {
    if (showWelcome) {
      localStorage.removeItem(SHOW_WELCOME_ONCE_KEY);
    }
  }, [showWelcome]);

  const hourly = [
    { time: "Now", temp: 23, Icon: Sun },
    { time: "1 PM", temp: 24, Icon: Sun },
    { time: "2 PM", temp: 25, Icon: Cloud },
    { time: "3 PM", temp: 25, Icon: Cloud },
    { time: "4 PM", temp: 24, Icon: CloudRain },
  ];
  const observation = environment?.observation;
  const factors = careRisk?.care_risk_decision.factor_scores ?? [];
  const hasCareRisk = Boolean(careRisk);
  const hasEnvironment = Boolean(observation);
  const topScore = hasCareRisk ? Math.round(careRisk?.care_risk_score.score ?? 0) : 0;
  const climateScore = sumFactorDelta(factors, [
    "humidity_percent",
    "aqi",
    "particulate_matter",
    "rain_monsoon_intensity",
  ]);
  const usageScore = sumFactorDelta(factors, ["daily_runtime_hours"]);
  const careScore = Math.max(0, topScore - climateScore - usageScore);
  const topDevice = {
    ...devices[0],
    score: topScore,
    climate: hasCareRisk ? climateScore : 0,
    usage: hasCareRisk ? usageScore : 0,
    care: hasCareRisk ? careScore : 0,
  };
  const triggerReason = hasCareRisk
    ? selectPrimaryTriggerReason(factors, careRisk?.care_risk_score.trigger_reason?.[0])
    : isCareRiskLoading
      ? "Updating care recommendation from your appliance and environment data..."
      : "Care recommendation is temporarily unavailable.";
  const temperatureLabel = hasEnvironment && observation?.temperature_c != null
    ? `${Math.round(observation.temperature_c)}°`
    : isEnvironmentLoading ? "..." : "--";
  const humidityLabel = hasEnvironment && observation?.humidity_percent != null
    ? `${Math.round(observation.humidity_percent)}%`
    : isEnvironmentLoading ? "..." : "--";
  const aqiLabel = hasEnvironment && observation?.aqi != null
    ? `${Math.round(observation.aqi)}`
    : isEnvironmentLoading ? "..." : "--";
  const pmSource = observation?.pm25 ?? observation?.pm10;
  const pmLabel = hasEnvironment && pmSource != null ? `${Math.round(pmSource)}` : isEnvironmentLoading ? "..." : "--";
  const locationLabel = hasEnvironment
    ? displayLocation(observation?.region, observation?.city)
    : displayLocation(profileLocation?.region, profileLocation?.city);

  return (
    <div className="relative min-h-full w-full overflow-x-hidden bg-[#f7f9f8]">
      {/* 留ㅼ슦 ????Aurora Glow */}
      <div className="pointer-events-none absolute -top-24 -left-20 w-80 h-80 rounded-full"
        style={{ background: "rgba(61,220,151,0.10)", filter: "blur(90px)" }} />
      <div className="pointer-events-none absolute top-[360px] -right-16 w-64 h-64 rounded-full"
        style={{ background: "rgba(100,210,190,0.09)", filter: "blur(80px)" }} />
      <div className="pointer-events-none absolute bottom-[180px] left-0 w-56 h-56 rounded-full"
        style={{ background: "rgba(80,200,160,0.08)", filter: "blur(75px)" }} />

      {isAiCareTransitioning && (
        <motion.div
          className="pointer-events-none absolute inset-0 z-40"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.24, ease: "easeOut" }}
          style={{
            background: "rgba(255,255,255,0.24)",
            backdropFilter: "blur(1.5px)",
            WebkitBackdropFilter: "blur(1.5px)",
          }}
        />
      )}

      <motion.div
        className="relative z-10 px-[18px] pt-[52px] pb-[14px] w-full max-w-[390px] mx-auto"
        animate={isAiCareTransitioning ? { opacity: 0.82, filter: "blur(1.5px)" } : { opacity: 1, filter: "blur(0px)" }}
        transition={{ duration: 0.24, ease: "easeOut" }}
      >

        {/* ?ㅻ뜑 */}
        <div className="mb-[6px] flex items-center pl-[5px] pt-[6px] pb-[4px]">
          <img src={careVisionLogo} alt="Care Vision" className="h-[17px] w-[121px]" />
        </div>
        <p className="mb-[26px] font-['Pretendard:Regular',sans-serif] text-[20px] font-normal tracking-[-0.36px] text-[#111]" style={{ paddingLeft: "5px" }}>
          {showWelcome ? "Welcome, " : ""}{displayName} 👋
        </p>

        {/* ?? AI Recommended Care 移대뱶 ?? */}
        {aiAlertVisible && <motion.button
          onClick={handleAiCareClick}
          className="mb-[14px] block w-full text-left"
          disabled={isAiCareTransitioning}
          animate={{ y: [0, -7, -3, 0], rotate: [0, -0.35, 0.22, 0] }}
          whileHover={{ scale: 1.018, y: -5, rotate: 0 }}
          whileTap={{ scale: 0.97 }}
          transition={{
            y: { duration: 3.2, repeat: Infinity, ease: "easeInOut" },
            rotate: { duration: 3.2, repeat: Infinity, ease: "easeInOut" },
            scale: { duration: 0.18, ease: [0.22, 1, 0.36, 1] },
          }}
        >
          <motion.div
            className="relative flex h-[120px] flex-shrink-0 items-center self-stretch overflow-hidden rounded-[20px] px-[16px] py-[18px]"
            style={{
              gap: "14px",
              border: "1.278px solid rgba(166, 244, 196, 0.75)",
              background: "linear-gradient(180deg, rgba(50, 208, 142, 0.20) 0%, rgba(237, 247, 187, 0.20) 100%)",
              boxShadow: "0 16px 38px 0 rgba(61, 220, 151, 0.16), 0 8px 18px 0 rgba(255, 141, 27, 0.11), 0 1px 0 0 rgba(255, 255, 255, 0.72) inset",
            }}
          >

            <div className="flex-shrink-0">
              <img src={acImage} alt="Air Conditioner" className="w-[75px] h-[75px] object-contain" />
            </div>

            <div className="relative flex-1 min-w-0">
              <div className="mb-[7px]">
                <span
                  className="inline-flex items-center rounded-full px-[11px] py-[3px] font-['Pretendard:SemiBold',sans-serif] text-[11px]"
                  style={{
                    background: "linear-gradient(135deg, #2ecc8a 0%, #3DDC97 100%)",
                    border: "1px solid rgba(255,255,255,0.35)",
                    color: "#ffffff",
                    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.45), 0 2px 8px rgba(29,184,122,0.25)",
                    textShadow: "0 1px 2px rgba(0,0,0,0.12)",
                  }}
                >
                  AI Care
                </span>
              </div>
              <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#333] leading-[18px]">
                {triggerReason}
              </p>
            </div>
          </motion.div>
        </motion.button>}

        {/* ?? ?좎뵪 ??쒕낫???? */}
        <div
          className="relative overflow-hidden rounded-[20px] px-[16px] py-[15px] mb-[14px]"
          style={glassCard}
        >
          {/* ?ㅻ뜑 */}
          <div className="flex items-center justify-between mb-[12px]">
            <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#555]">{locationLabel}</p>
            <div
              className="inline-flex shrink-0 items-center gap-[4px] rounded-full px-[10px] py-[4px] font-['Pretendard:SemiBold',sans-serif] text-[11px]"
              style={{ background: "rgba(61,220,151,0.08)", border: "1px solid rgba(61,220,151,0.22)" }}
            >
              <Cloud size={12} className="text-[#3BA7FF]" />
              <span className="text-[#111]">{temperatureLabel}</span>
              <span className="font-['Pretendard:Medium',sans-serif] text-[#888]">Cloudy</span>
            </div>
          </div>

          {/* 2횞2 洹몃━????紐⑤몢 ?듭씪??Glass 諛곌꼍, ?ъ씤?몃쭔 ?ㅻ쫫 */}
          <div className="grid grid-cols-2 gap-[8px]">
            {/* Temperature ???몃옉 ?ъ씤??*/}
            <div
              className="rounded-[14px] px-[13px] py-[10px] flex items-center gap-[10px]"
              style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.85)", boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)" }}
            >
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center flex-shrink-0"
                style={{ background: "rgba(251,191,36,0.12)" }}>
                <TemperatureIcon />
              </div>
              <div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">Temperature</p>
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[20px] text-[#111] leading-tight">{temperatureLabel}</p>
              </div>
            </div>

            {/* Humidity ??誘쇳듃 ?ъ씤??*/}
            <div
              className="rounded-[14px] px-[13px] py-[10px] flex items-center gap-[10px]"
              style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.85)", boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)" }}
            >
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center flex-shrink-0"
                style={{ background: "rgba(61,220,151,0.10)" }}>
                <Droplets size={17} className="text-[#1AA9C2E0]" />
              </div>
              <div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">Humidity</p>
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[20px] text-[#111] leading-tight">{humidityLabel}</p>
              </div>
            </div>

            {/* 嫄댁“湲????고븳 誘쇳듃 ?ъ씤??*/}
            <div
              className="rounded-[14px] px-[13px] py-[10px] flex items-center gap-[10px]"
              style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.85)", boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)" }}
            >
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center flex-shrink-0"
                style={{ background: "#64D2BE1A" }}>
                <AirQualityIcon />
              </div>
              <div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">Air Quality</p>
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[17px] text-[#111] leading-tight">
                  <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#aaa]">AQI</span> {aqiLabel}
                </p>
              </div>
            </div>

            {/* Washing Machine ???고븳 ?쇰깽???ъ씤??*/}
            <div
              className="rounded-[14px] px-[13px] py-[10px] flex items-center gap-[10px]"
              style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.85)", boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)" }}
            >
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center flex-shrink-0"
                style={{ background: "rgba(160,150,220,0.10)" }}>
                <FineDustIcon />
              </div>
              <div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">Fine Dust</p>
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[17px] text-[#111] leading-tight">
                  <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#aaa]">pm</span> {pmLabel}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ?? Care Risk Score ?? */}
        {(() => {
          const loadingRisk = isCareRiskLoading && !hasCareRisk;
          const riskLevel = careRisk?.care_risk_score.risk_level;
          const riskMeta = loadingRisk
            ? { text: "text-[#888]", label: "Updating", hex: "#9CA3AF" }
            : getRiskColor(topScore, riskLevel);
          const comment = loadingRisk ? "Updating care risk score..." : getRiskComment(topScore, riskLevel);
          const scoreColor = loadingRisk ? "#9CA3AF" : getGaugeScoreColor(topScore, riskLevel);
          return (
            <div
              className="relative overflow-hidden rounded-[20px] px-[16px] pt-[15px] pb-[16px] mb-[14px]"
              style={glassCard}
            >
              <div className="mb-[12px]">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#555]">Care Risk Score</p>
                  <span
                    className={`font-['Pretendard:SemiBold',sans-serif] text-[11px] ${riskMeta.text} px-[10px] py-[4px] rounded-full shrink-0`}
                    style={{ background: `${riskMeta.hex}12`, border: `1px solid ${riskMeta.hex}35` }}
                  >
                    {riskMeta.label}
                  </span>
                </div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888] mt-[2px]">{comment}</p>
              </div>

              <SegmentedGauge
                climate={topDevice.climate}
                usage={topDevice.usage}
                care={topDevice.care}
                scoreColor={scoreColor}
              />
            </div>
          );
        })()}

        {/* ?? Today's Recommended Care Video ?? */}
        <div
          className="relative block w-full text-left overflow-hidden rounded-[20px] px-[18px] py-[18px]"
          style={{
            background: "linear-gradient(135deg, #1DB87A 0%, #3DDC97 50%, #6ee7b7 100%)",
            boxShadow: "0 10px 32px rgba(29,184,122,0.28)",
          }}
        >
          <div className="pointer-events-none absolute -top-6 -right-6 w-28 h-28 rounded-full"
            style={{ background: "rgba(255,255,255,0.15)", filter: "blur(20px)" }} />
          <p className="relative font-['Pretendard:Medium',sans-serif] text-[12px] text-white/75 mb-[5px]">
            Today's Recommended Care Video
          </p>
          <p className="relative font-['Pretendard:SemiBold',sans-serif] text-[16px] text-white">
            How to Clean the Air Conditioner Filter
          </p>
        </div>

      </motion.div>
    </div>
  );
}


import { useParams, useNavigate } from "react-router";
import { ChevronLeft, Snowflake } from "lucide-react";
import imgImage6 from "../../imports/제품페이지관리/47f735f974d0900368394246ff236d4a45df2a58.png";

const recentHistory = [
  { id: "r1", type: "Self Care", title: "Air Conditioner Filter Cleaning", date: "2 days ago" },
  { id: "r2", type: "Self A/S", title: "Remote Pairing", date: "1 week ago" },
  { id: "r3", type: "Self Care", title: "Outdoor Unit Exterior Check", date: "2 weeks ago" },
];

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

const innerCard = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
  border: "1px solid rgba(255,255,255,0.85)",
  boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)",
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
      <g clipPath="url(#device-temperature-icon-clip)">
        <path d="M9.90804 2.83047V10.2898C10.4477 10.6014 10.8695 11.0823 11.108 11.6581C11.3465 12.2338 11.3883 12.8722 11.227 13.4741C11.0657 14.076 10.7103 14.6079 10.2159 14.9873C9.72154 15.3666 9.11578 15.5723 8.49261 15.5723C7.86944 15.5723 7.26368 15.3666 6.76929 14.9873C6.27489 14.6079 5.91949 14.076 5.7582 13.4741C5.59692 12.8722 5.63875 12.2338 5.87723 11.6581C6.11571 11.0823 6.5375 10.6014 7.07718 10.2898V2.83047C7.07718 2.45508 7.2263 2.09506 7.49175 1.82961C7.75719 1.56416 8.11721 1.41504 8.49261 1.41504C8.86801 1.41504 9.22803 1.56416 9.49347 1.82961C9.75892 2.09506 9.90804 2.45508 9.90804 2.83047Z" stroke="#FF694B" strokeWidth="1.41543" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M8.66089 8.35059H9.66089M8.66089 6.35059H9.66089M8.66089 10.3506H9.66089" stroke="#FF694B" strokeLinecap="round" />
      </g>
      <defs>
        <clipPath id="device-temperature-icon-clip">
          <rect width="16.9852" height="16.9852" fill="white" />
        </clipPath>
      </defs>
    </svg>
  );
}

function AirFlowIcon() {
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

export function DeviceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const careCount = 5;
  const asCount = 2;

  return (
    <div className="relative min-h-full w-full overflow-x-hidden bg-[#f7f9f8]">
      <div
        className="pointer-events-none absolute -top-20 -left-16 w-72 h-72 rounded-full"
        style={{ background: "rgba(61,220,151,0.09)", filter: "blur(90px)" }}
      />
      <div
        className="pointer-events-none absolute top-[300px] -right-12 w-56 h-56 rounded-full"
        style={{ background: "rgba(100,210,190,0.08)", filter: "blur(80px)" }}
      />

      <div className="relative z-10 px-[18px] pt-[40px] pb-[20px] w-full max-w-[390px] mx-auto">
        <div className="flex items-center gap-1 mb-5 -mx-[2px]">
          <button onClick={() => navigate("/device")} className="p-1">
            <ChevronLeft size={22} className="text-[#555]" />
          </button>
          <p className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-[15px]">
            Product Details
          </p>
        </div>

        <div className="rounded-[20px] p-5 mb-4" style={glass}>
          <div className="relative flex justify-center mb-1 pt-[24px]">
            <span className="absolute top-0 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-[#BFEAD4] bg-[#eaf8f1] px-[10px] py-[3px] font-['Pretendard:Medium',sans-serif] text-[9px] text-[#2d9b69]">
              LG Whisen Wall-mounted
            </span>
            <img src={imgImage6} alt="Air Conditioner" className="w-[200px] h-[100px] object-contain" />
          </div>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-[#111] text-center mb-3">Living Room Air Conditioner</p>
          <p className="hidden">
            LG Whisen Wall-mounted · Product #{id}
          </p>
          <div className="grid grid-cols-2 pt-4" style={{ borderTop: "1px solid rgba(200,200,200,0.25)" }}>
            <div className="flex flex-col items-center gap-[4px] border-r border-[rgba(200,200,200,0.28)] px-2">
              <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#999]">Product Type</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[13px] leading-tight text-[#111]">Air Conditioner</p>
            </div>
            <div className="flex flex-col items-center gap-[4px] px-2">
              <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#999]">Registered Date</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[13px] leading-tight text-[#111]">2024.01.15</p>
            </div>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-[20px] px-[16px] pt-[15px] pb-[16px] mb-[14px]" style={{ ...glass, background: "rgba(242,252,250,0.62)" }}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#555] mb-[12px]">Product Status</p>
          <div className="grid grid-cols-3 gap-[8px]">
            <div className="min-h-[96px] rounded-[14px] px-2 py-3 flex flex-col items-center justify-center gap-[6px]" style={innerCard}>
              <div
                className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center"
                style={{ background: "rgba(145,205,255,0.18)" }}
              >
                <Snowflake size={16} className="text-[#2060b0]" />
              </div>
              <p className="h-[13px] whitespace-nowrap font-['Pretendard:Medium',sans-serif] text-[10px] leading-[13px] text-[#888]">Mode</p>
              <p className="h-[17px] font-['Pretendard:SemiBold',sans-serif] text-[14px] leading-[17px] text-[#111]">Cooling</p>
            </div>
            <div className="min-h-[96px] rounded-[14px] px-2 py-3 flex flex-col items-center justify-center gap-[6px] [&>p:first-of-type]:hidden" style={innerCard}>
              <div
                className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center"
                style={{ background: "rgba(251,191,36,0.12)" }}
              >
                <TemperatureIcon />
              </div>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[14px] text-[#111]">23°</p>
              <p className="h-[13px] whitespace-nowrap font-['Pretendard:Medium',sans-serif] text-[10px] leading-[13px] text-[#888]">Temperature</p>
              <p className="h-[17px] font-['Pretendard:SemiBold',sans-serif] text-[14px] leading-[17px] text-[#111]">23&deg;</p>
            </div>
            <div className="min-h-[96px] rounded-[14px] px-2 py-3 flex flex-col items-center justify-center gap-[6px]" style={innerCard}>
              <div
                className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center"
                style={{ background: "#64D2BE1A" }}
              >
                <AirFlowIcon />
              </div>
              <p className="h-[13px] whitespace-nowrap font-['Pretendard:Medium',sans-serif] text-[10px] leading-[13px] text-[#888]">Fan Speed</p>
              <p className="h-[17px] font-['Pretendard:SemiBold',sans-serif] text-[14px] leading-[17px] text-[#111]">Auto</p>
            </div>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-[20px] px-[16px] pt-[15px] pb-[16px] mb-[14px]" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#555] mb-[12px]">Care Summary</p>
          <div className="grid grid-cols-2 gap-3 mb-1">
            <div
              className="rounded-[16px] overflow-hidden"
              style={{
                padding: "1px",
                background: "linear-gradient(180deg, rgba(255,255,255,0.64), rgba(255,255,255,0.38))",
                backdropFilter: "blur(18px)",
                WebkitBackdropFilter: "blur(18px)",
                border: "1px solid rgba(61,220,151,0.18)",
                boxShadow: "0 9px 20px rgba(31,69,61,0.07), inset 0 1px 0 rgba(255,255,255,0.88)",
              }}
            >
              <div
                className="relative overflow-hidden rounded-[15px] py-3 px-3 text-center flex flex-col items-center gap-[5px]"
                style={{
                  background: "rgba(61,220,151,0.12)",
                  backdropFilter: "blur(14px)",
                  WebkitBackdropFilter: "blur(14px)",
                  border: "1px solid rgba(61,220,151,0.18)",
                  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.88), inset 0 -10px 18px rgba(22,163,74,0.05)",
                }}
              >
                <span style={{ fontFamily: "Pretendard,sans-serif", fontSize: 25, fontWeight: 800, color: "#159B63", lineHeight: 1 }}>
                  {careCount}
                </span>
                <div style={{ width: "28%", height: "1px", background: "rgba(21,155,99,0.28)", borderRadius: 99 }} />
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px]" style={{ color: "#5D7169" }}>Self Care</p>
              </div>
            </div>
            <div
              className="rounded-[16px] overflow-hidden"
              style={{
                padding: "1px",
                background: "linear-gradient(180deg, rgba(255,255,255,0.64), rgba(255,255,255,0.38))",
                backdropFilter: "blur(18px)",
                WebkitBackdropFilter: "blur(18px)",
                border: "1px solid rgba(250,204,21,0.24)",
                boxShadow: "0 9px 20px rgba(31,69,61,0.07), inset 0 1px 0 rgba(255,255,255,0.88)",
              }}
            >
              <div
                className="relative overflow-hidden rounded-[15px] py-3 px-3 text-center flex flex-col items-center gap-[5px]"
                style={{
                  background: "rgba(250,204,21,0.14)",
                  backdropFilter: "blur(14px)",
                  WebkitBackdropFilter: "blur(14px)",
                  border: "1px solid rgba(250,204,21,0.24)",
                  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.88), inset 0 -10px 18px rgba(202,138,4,0.05)",
                }}
              >
                <span style={{ fontFamily: "Pretendard,sans-serif", fontSize: 25, fontWeight: 800, color: "#FACC15", lineHeight: 1 }}>
                  {asCount}
                </span>
                <div style={{ width: "28%", height: "1px", background: "rgba(202,138,4,0.32)", borderRadius: 99 }} />
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px]" style={{ color: "#6F6F67" }}>Self A/S</p>
              </div>
            </div>
          </div>
          <div className="pt-3 mt-3" style={{ borderTop: "1px solid rgba(200,200,200,0.25)" }}>
            <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888] mb-1">Recent Care Details</p>
            <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#111]">
              {recentHistory[0].title} · {recentHistory[0].date}
            </p>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-[20px] px-[16px] pt-[15px] pb-[16px] mb-[14px]" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#555] mb-[12px]">Care History</p>
          <div className="space-y-3">
            {recentHistory.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span
                    className="py-0.5 rounded-[6px] font-['Pretendard:Medium',sans-serif] text-[11px] text-center inline-block shrink-0"
                    style={{
                      minWidth: "64px",
                      ...(item.type === "Self Care"
                          ? {
                              background: "rgba(61,220,151,0.12)",
                            color: "#159B63",
                            border: "1px solid rgba(61,220,151,0.18)",
                            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.72)",
                          }
                        : {
                            background: "rgba(250,204,21,0.14)",
                            color: "#e48e2d",
                            border: "1px solid rgba(250,204,21,0.24)",
                            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.72)",
                          }),
                    }}
                  >
                    {item.type}
                  </span>
                  <p className="font-['Pretendard:Medium',sans-serif] text-[13px] leading-[17px] text-[#222] truncate">
                    {item.title}
                  </p>
                </div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[10px] leading-[13px] text-[#999] shrink-0">{item.date}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

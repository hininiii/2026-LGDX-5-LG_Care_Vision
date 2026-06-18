import { useParams, useNavigate } from "react-router";
import { ChevronLeft, Snowflake, Thermometer, Wind } from "lucide-react";
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

      <div className="relative z-10 px-[18px] pt-[39px] pb-[20px] w-full max-w-[390px] mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => navigate("/device")} className="p-1">
            <ChevronLeft size={24} className="text-[#555]" />
          </button>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[20px] tracking-[-0.3px] text-[#111]">
            Product Details
          </p>
        </div>

        <div className="rounded-[20px] p-5 mb-4" style={glass}>
          <div className="flex justify-center mb-4">
            <img src={imgImage6} alt="Air Conditioner" className="w-[200px] h-[100px] object-contain" />
          </div>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[18px] text-[#111] text-center mb-1">Living Room Air Conditioner</p>
          <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] text-center mb-4">
            LG Whisen Wall-mounted · Product #{id}
          </p>
          <div className="grid grid-cols-2 gap-2 pt-4" style={{ borderTop: "1px solid rgba(200,200,200,0.25)" }}>
            <div className="flex justify-between">
              <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#999]">Product Type</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#111]">Air Conditioner</p>
            </div>
            <div className="flex justify-between">
              <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#999]">Registered Date</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#111]">2024.01.15</p>
            </div>
          </div>
        </div>

        <div className="rounded-[20px] p-5 mb-4" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-4">Product Status</p>
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-[14px] p-3 flex flex-col items-center gap-1" style={innerCard}>
              <div
                className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center"
                style={{ background: "rgba(145,205,255,0.18)" }}
              >
                <Snowflake size={16} className="text-[#2060b0]" />
              </div>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[14px] text-[#111]">Cooling</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">Mode</p>
            </div>
            <div className="rounded-[14px] p-3 flex flex-col items-center gap-1" style={innerCard}>
              <div
                className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center"
                style={{ background: "rgba(251,191,36,0.12)" }}
              >
                <Thermometer size={16} className="text-[#d97706]" />
              </div>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[14px] text-[#111]">23°</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">Set Temperature</p>
            </div>
            <div className="rounded-[14px] p-3 flex flex-col items-center gap-1" style={innerCard}>
              <div
                className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center"
                style={{ background: "rgba(61,220,151,0.10)" }}
              >
                <Wind size={16} className="text-[#1DB87A]" />
              </div>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[14px] text-[#111]">Auto</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">Fan Speed</p>
            </div>
          </div>
        </div>

        <div className="rounded-[20px] p-5 mb-4" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-4">Care Summary</p>
          <div className="grid grid-cols-2 gap-3 mb-1 px-1">
            <div
              className="rounded-[16px] overflow-hidden"
              style={{
                padding: "1px",
                background: "linear-gradient(145deg, rgba(255,255,255,0.95), rgba(134,213,160,0.6))",
                boxShadow: "0 4px 16px rgba(120,200,140,0.18)",
              }}
            >
              <div
                className="rounded-[15px] py-5 px-3 text-center flex flex-col items-center gap-2"
                style={{ background: "linear-gradient(145deg, rgba(210,244,220,0.55), rgba(230,248,235,0.35))" }}
              >
                <span style={{ fontFamily: "Pretendard,sans-serif", fontSize: 32, fontWeight: 800, color: "#16a34a", lineHeight: 1 }}>
                  {careCount}
                </span>
                <div style={{ width: "40%", height: "1px", background: "rgba(22,163,74,0.25)", borderRadius: 99 }} />
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px]" style={{ color: "#16a34a" }}>Self Care Count</p>
              </div>
            </div>
            <div
              className="rounded-[16px] overflow-hidden"
              style={{
                padding: "1px",
                background: "linear-gradient(145deg, rgba(255,255,255,0.95), rgba(253,211,77,0.6))",
                boxShadow: "0 4px 16px rgba(250,200,60,0.18)",
              }}
            >
              <div
                className="rounded-[15px] py-5 px-3 text-center flex flex-col items-center gap-2"
                style={{ background: "linear-gradient(145deg, rgba(255,243,180,0.55), rgba(255,249,210,0.35))" }}
              >
                <span style={{ fontFamily: "Pretendard,sans-serif", fontSize: 32, fontWeight: 800, color: "#ca8a04", lineHeight: 1 }}>
                  {asCount}
                </span>
                <div style={{ width: "40%", height: "1px", background: "rgba(202,138,4,0.25)", borderRadius: 99 }} />
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[11px]" style={{ color: "#ca8a04" }}>Self Service Count</p>
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

        <div className="rounded-[20px] p-5" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-3">Recent Care History</p>
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
                            color: "#0f8a58",
                            border: "1px solid rgba(29,184,122,0.22)",
                          }
                        : {
                            background: "rgba(253,211,77,0.18)",
                            color: "#ca8a04",
                            border: "1px solid rgba(202,138,4,0.22)",
                          }),
                    }}
                  >
                    {item.type}
                  </span>
                  <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#111] truncate">
                    {item.title}
                  </p>
                </div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888] shrink-0">{item.date}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

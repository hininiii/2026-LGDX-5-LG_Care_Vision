import { useState } from "react";
import { useNavigate, useLocation } from "react-router";
import { PieChart, Pie, Cell } from "recharts";
import { Cloud, CloudRain, Sun, Droplets, Wind, Thermometer, AirVent, RotateCcw, Tv, Refrigerator } from "lucide-react";
import chatbotGif from "../../imports/LG______.gif";
import acImage from "../../imports/제품페이지관리/47f735f974d0900368394246ff236d4a45df2a58.png";

const devices = [
  { id: 1, name: "에어컨", Icon: AirVent, score: 82, climate: 35, usage: 28, care: 19 },
  { id: 2, name: "세탁기", Icon: RotateCcw, score: 61, climate: 18, usage: 24, care: 19 },
  { id: 3, name: "TV", Icon: Tv, score: 44, climate: 12, usage: 20, care: 12 },
  { id: 4, name: "냉장고", Icon: Refrigerator, score: 31, climate: 8, usage: 14, care: 9 },
];

function getRiskColor(score: number) {
  if (score >= 75) return { text: "text-[#ff4c49]", bar: "bg-[#ff4c49]", label: "주의 필요", hex: "#ff4c49" };
  if (score >= 50) return { text: "text-[#f59e0b]", bar: "bg-[#f59e0b]", label: "보통", hex: "#f59e0b" };
  return { text: "text-[#22c55e]", bar: "bg-[#22c55e]", label: "양호", hex: "#22c55e" };
}

function getRiskComment(score: number) {
  if (score >= 75) return "일부 기기의 케어가 필요합니다.";
  if (score >= 50) return "기기 관리 상태가 양호합니다.";
  return "기기 관리가 잘 되고 있습니다~!";
}

const glassCard: React.CSSProperties = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

function SegmentedGauge({ climate, usage, care }: { climate: number; usage: number; care: number }) {
  const total = climate + usage + care;
  const totalMax = 105;
  const remaining = totalMax - total;

  // 위험도 높을수록 레드 → 채움 반전 (max - value = 안전 여유분, 작을수록 위험)
  const climateRisk = climate; // 35/40 → 위험도 높음
  const usageRisk   = usage;   // 28/40
  const careRisk    = care;    // 19/25

  // 위험도 비율: 높을수록 레드에 가깝게, 색상도 위험도 순으로 재배치
  const pieData = [
    { name: "기후", value: climateRisk, fill: "url(#grad-climate)" }, // 가장 위험 → 레드
    { name: "사용", value: usageRisk,   fill: "url(#grad-usage)" },   // 중간 → 주황
    { name: "관리", value: careRisk,    fill: "url(#grad-care)" },    // 낮음 → 민트
    { name: "미달", value: remaining,   fill: "url(#grad-empty)" },
  ];

  const stats = [
    { label: "기후", value: climate, color: "#FF7A7A", glow: "rgba(255,122,122,0.22)" },
    { label: "사용", value: usage,   color: "#FFE89A", glow: "rgba(255,232,154,0.30)" },
    { label: "관리", value: care,    color: "#48D6A6", glow: "rgba(72,214,166,0.22)" },
  ];

  return (
    <div className="flex flex-col items-center w-full">
      {/* 차트 글래스 컨테이너 */}
      <div className="relative w-full rounded-[20px] flex flex-col items-center pt-[14px] pb-[10px]"
        style={{
          background: "rgba(255,255,255,0.45)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          border: "1px solid rgba(255,255,255,0.75)",
          boxShadow: "0 8px 32px rgba(61,220,151,0.08), 0 2px 8px rgba(255,107,104,0.06), inset 0 1px 0 rgba(255,255,255,0.95)",
        }}
      >
        {/* 배경 컬러 glow */}
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

          {/* 중앙 점수 */}
          <div className="absolute inset-0 flex items-end justify-center pb-[4px] pointer-events-none">
            <span style={{ fontFamily: "Pretendard, sans-serif" }}>
              <span style={{ fontSize: 28, fontWeight: 800, color: "#FF7A7A", lineHeight: 1 }}>{total}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#aaa", marginLeft: 1 }}>점</span>
            </span>
          </div>
        </div>
      </div>

      {/* 기후 / 사용 / 관리 수치 — 글래스모피즘 */}
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
            <span style={{ fontSize: 9, color: "#999", fontFamily: "Pretendard, sans-serif", marginTop: 4 }}>{s.label}</span>
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

  const hourly = [
    { time: "지금", temp: 23, Icon: Sun },
    { time: "13시", temp: 24, Icon: Sun },
    { time: "14시", temp: 25, Icon: Cloud },
    { time: "15시", temp: 25, Icon: Cloud },
    { time: "16시", temp: 24, Icon: CloudRain },
  ];

  return (
    <div className="relative min-h-full w-full overflow-x-hidden bg-[#f7f9f8]">
      {/* 매우 은은한 Aurora Glow */}
      <div className="pointer-events-none absolute -top-24 -left-20 w-80 h-80 rounded-full"
        style={{ background: "rgba(61,220,151,0.10)", filter: "blur(90px)" }} />
      <div className="pointer-events-none absolute top-[360px] -right-16 w-64 h-64 rounded-full"
        style={{ background: "rgba(100,210,190,0.09)", filter: "blur(80px)" }} />
      <div className="pointer-events-none absolute bottom-[180px] left-0 w-56 h-56 rounded-full"
        style={{ background: "rgba(80,200,160,0.08)", filter: "blur(75px)" }} />

      <div className="relative z-10 px-[18px] pt-[38px] pb-[110px] w-full max-w-[390px] mx-auto">

        {/* 헤더 */}
        <p className="font-['Pretendard:SemiBold',sans-serif] text-[20px] tracking-[-0.3px] text-[#111] mb-[6px]" style={{ paddingLeft: "5px" }}>
          Care Vision
        </p>
        <p className="font-['Pretendard:SemiBold','Noto_Sans_Devanagari:SemiBold',sans-serif] text-[22px] tracking-[-0.36px] text-[#111] mb-[20px]" style={{ paddingLeft: "5px" }}>
          환영합니다. तनीषा जी! 👋
        </p>

        {/* ── AI 추천 관리 카드 ── */}
        {aiAlertVisible && <button onClick={() => navigate("/self-care")} className="block w-full text-left mb-[12px]">
          <div
            className="relative overflow-hidden rounded-[20px] px-[16px] py-[18px] flex items-center gap-[14px]"
            style={{
              background: "rgba(255,255,255,0.25)",
              backdropFilter: "blur(16px)",
              WebkitBackdropFilter: "blur(16px)",
              border: "1px solid rgba(255,255,255,0.5)",
              boxShadow: "0 8px 32px rgba(255,141,27,0.10), inset 0 1px 0 rgba(255,255,255,0.7)",
            }}
          >

            <div className="flex-shrink-0">
              <img src={acImage} alt="에어컨" className="w-[75px] h-[75px] object-contain" />
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
                  AI 추천 관리
                </span>
              </div>
              <p className="font-['Pretendard:Medium',sans-serif] text-[13px] text-[#333] leading-[18px]">
                오늘 대기질 나쁨 · 에어컨 필터 점검을 권장합니다.
              </p>
            </div>
          </div>
        </button>}

        {/* ── 날씨 대시보드 ── */}
        <div
          className="relative overflow-hidden rounded-[20px] px-[16px] py-[15px] mb-[14px]"
          style={glassCard}
        >
          {/* 헤더 */}
          <div className="flex items-center justify-between mb-[12px]">
            <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#555]">뉴델리 · 오늘</p>
            <div
              className="flex items-center gap-[5px] rounded-full px-[9px] py-[4px]"
              style={{ background: "rgba(61,220,151,0.08)", border: "1px solid rgba(61,220,151,0.22)" }}
            >
              <Cloud size={13} className="text-[#3DDC97]" />
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[12px] text-[#111]">26°</p>
              <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">흐림</p>
            </div>
          </div>

          {/* 2×2 그리드 — 모두 통일된 Glass 배경, 포인트만 다름 */}
          <div className="grid grid-cols-2 gap-[8px]">
            {/* 온도 — 노랑 포인트 */}
            <div
              className="rounded-[14px] px-[13px] py-[10px] flex items-center gap-[10px]"
              style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.85)", boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)" }}
            >
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center flex-shrink-0"
                style={{ background: "rgba(251,191,36,0.12)" }}>
                <Thermometer size={17} className="text-[#d97706]" />
              </div>
              <div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">온도</p>
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[20px] text-[#111] leading-tight">24°</p>
              </div>
            </div>

            {/* 습도 — 민트 포인트 */}
            <div
              className="rounded-[14px] px-[13px] py-[10px] flex items-center gap-[10px]"
              style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.85)", boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)" }}
            >
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center flex-shrink-0"
                style={{ background: "rgba(61,220,151,0.10)" }}>
                <Droplets size={17} className="text-[#1DB87A]" />
              </div>
              <div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">습도</p>
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[20px] text-[#111] leading-tight">56%</p>
              </div>
            </div>

            {/* 건조기 — 연한 민트 포인트 */}
            <div
              className="rounded-[14px] px-[13px] py-[10px] flex items-center gap-[10px]"
              style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.85)", boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)" }}
            >
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center flex-shrink-0"
                style={{ background: "rgba(100,210,190,0.10)" }}>
                <Wind size={16} className="text-[#2aaa8a]" />
              </div>
              <div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">대기질</p>
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[17px] text-[#111] leading-tight">
                  <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#aaa]">AQI</span> 10
                </p>
              </div>
            </div>

            {/* 세탁기 — 연한 라벤더 포인트 */}
            <div
              className="rounded-[14px] px-[13px] py-[10px] flex items-center gap-[10px]"
              style={{ background: "rgba(255,255,255,0.55)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", border: "1px solid rgba(255,255,255,0.85)", boxShadow: "0 2px 12px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)" }}
            >
              <div className="w-[32px] h-[32px] rounded-[10px] flex items-center justify-center flex-shrink-0"
                style={{ background: "rgba(160,150,220,0.10)" }}>
                <Droplets size={16} className="text-[#8080c0]" />
              </div>
              <div>
                <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888]">미세 먼지</p>
                <p className="font-['Pretendard:SemiBold',sans-serif] text-[17px] text-[#111] leading-tight">
                  <span className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#aaa]">pm</span> 10
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Care Risk Score ── */}
        <p className="font-['Pretendard:Bold',sans-serif] text-[16px] text-[#000] mb-[10px]" style={{ paddingLeft: "5px" }}>Care Risk Score</p>
        {(() => {
          const topScore = devices[0].score;
          const { text, label, hex } = getRiskColor(topScore);
          const comment = getRiskComment(topScore);
          const topDevice = devices[0];
          return (
            <div
              className="relative overflow-hidden rounded-[20px] px-[16px] pt-[15px] pb-[16px] mb-[14px]"
              style={glassCard}
            >
              <div className="flex items-start justify-between gap-3 mb-[12px]">
                <div className="min-w-0">
                  <p className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#222]">{comment}</p>
                  <p className="font-['Pretendard:Medium',sans-serif] text-[11px] text-[#888] mt-[2px]">에어컨 · 필터와 실내 환경 기준</p>
                </div>
                <span
                  className={`font-['Pretendard:SemiBold',sans-serif] text-[11px] ${text} px-[10px] py-[4px] rounded-full shrink-0`}
                  style={{ background: `${hex}12`, border: `1px solid ${hex}35` }}
                >
                  {label}
                </span>
              </div>

              <SegmentedGauge
                climate={topDevice.climate}
                usage={topDevice.usage}
                care={topDevice.care}
              />
            </div>
          );
        })()}

        {/* ── 오늘의 추천 관리 영상 ── */}
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
            오늘의 추천 관리 영상
          </p>
          <p className="relative font-['Pretendard:SemiBold',sans-serif] text-[16px] text-white">
            에어컨 필터 청소 방법
          </p>
        </div>

        {/* ── 챗봇 플로팅 버튼 ── */}
        <div className="fixed bottom-[130px] right-[calc(50%-165px)] z-50">
          <button onClick={() => navigate("/chat")} className="p-0">
            <img
              src={chatbotGif}
              alt="챗봇"
              className="w-[78px] h-[78px] rounded-full cursor-pointer hover:scale-110 transition-transform drop-shadow-lg"
            />
          </button>
        </div>

      </div>
    </div>
  );
}

import { useState } from "react";
import { Link } from "react-router";
import { X } from "lucide-react";
import acImage from "../../imports/제품페이지관리/47f735f974d0900368394246ff236d4a45df2a58.png";

const VALID_CODES: Record<string, { name: string; model: string }> = {
  "LG-WS-001": { name: "거실 에어컨", model: "LG 휘센 벽걸이" },
  "LG-WS-002": { name: "안방 에어컨", model: "LG 휘센 벽걸이" },
  "LG-WS-003": { name: "주방 에어컨", model: "LG 휘센 스탠드" },
};

interface RegisteredDevice {
  id: string;
  code: string;
  name: string;
  model: string;
  status: string;
}

const initialDevices: RegisteredDevice[] = [
  { id: "1", code: "LG-WS-001", name: "거실 에어컨", model: "LG 휘센 벽걸이", status: "정상" },
  { id: "2", code: "LG-WS-002", name: "안방 에어컨", model: "LG 휘센 벽걸이", status: "정상" },
];

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

export function Device() {
  const [devices, setDevices] = useState<RegisteredDevice[]>(initialDevices);
  const [showModal, setShowModal] = useState(false);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  const handleRegister = () => {
    setError("");
    const trimmed = code.trim().toUpperCase();
    const matched = VALID_CODES[trimmed];
    if (!matched) { setError("유효하지 않은 제품 코드입니다."); return; }
    if (devices.some((d) => d.code === trimmed)) { setError("이미 등록된 제품입니다."); return; }
    setDevices((prev) => [...prev, { id: Date.now().toString(), code: trimmed, name: matched.name, model: matched.model, status: "정상" }]);
    setCode("");
    setShowModal(false);
  };

  return (
    <div className="relative min-h-full w-full overflow-hidden bg-[#f7f9f8]">
      <div className="pointer-events-none absolute -top-20 -left-16 w-72 h-72 rounded-full"
        style={{ background: "rgba(61,220,151,0.09)", filter: "blur(90px)" }} />
      <div className="pointer-events-none absolute top-[300px] -right-12 w-56 h-56 rounded-full"
        style={{ background: "rgba(100,210,190,0.08)", filter: "blur(80px)" }} />

      <div className="relative z-10 px-[18px] pt-[38px] pb-[12px] w-full max-w-[390px] mx-auto">
        <p className="font-['Pretendard:SemiBold',sans-serif] text-[20px] tracking-[-0.3px] text-[#111] mb-[20px] pl-[5px] pt-[10px]">
          내 기기
        </p>

        <div className="space-y-3">
          {devices.map((device) => (
            <Link key={device.id} to={`/device/${device.id}`} className="block">
              <div className="rounded-[20px] p-4 flex items-center gap-4 transition-transform hover:scale-[1.01]" style={glass}>
                <div className="w-[72px] h-[72px] flex items-center justify-center flex-shrink-0">
                  <img src={acImage} alt="에어컨" className="w-[68px] h-[68px] object-contain" />
                </div>
                <div className="flex-1">
                  <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-[#111] mb-[3px]">{device.name}</p>
                  <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] mb-2">{device.model}</p>
                  <span className="inline-flex items-center px-3 py-1 rounded-full font-['Pretendard:Medium',sans-serif] text-[11px]"
                    style={{ background: "rgba(61,220,151,0.12)", border: "1px solid rgba(29,184,122,0.25)", color: "#0f8a58" }}>
                    {device.status}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>

        <div className="mt-4 rounded-[20px] p-6 text-center" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-[#111] mb-2">더 많은 제품을 등록하세요</p>
          <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] mb-4">
            제품 코드를 입력하면 맞춤 관리 서비스를 받을 수 있습니다
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="text-white px-6 py-3 rounded-[12px] font-['Pretendard:Medium',sans-serif] text-[14px]"
            style={{
              background: "linear-gradient(135deg, #24C99A 0%, #14B989 100%)",
              boxShadow: "0 4px 16px rgba(34,197,154,0.30), inset 0 1px 0 rgba(255,255,255,0.25)",
            }}
          >
            제품 코드로 등록하기
          </button>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 px-6" style={{ backdropFilter: "blur(4px)" }}>
          <div
            className="rounded-[20px] w-full max-w-[320px] p-6 relative"
            style={{
              background: "rgba(255,255,255,0.72)",
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
              boxShadow: "0 8px 40px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.8)",
            }}
          >
            <button
              onClick={() => { setShowModal(false); setCode(""); setError(""); }}
              className="absolute top-4 right-4 w-7 h-7 rounded-full flex items-center justify-center"
              style={{ background: "rgba(0,0,0,0.07)" }}
            >
              <X size={14} className="text-[#606060]" strokeWidth={2.5} />
            </button>

            <p className="font-['Pretendard:SemiBold',sans-serif] text-[18px] text-[#111] mb-1">제품 코드 입력</p>
            <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] mb-4">
              제품 박스 또는 본체에 표기된 제품 코드를 입력해주세요.
            </p>

            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="예: LG-WS-001"
              autoFocus
              className="w-full rounded-[12px] px-4 py-3 font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] outline-none mb-2"
              style={{
                background: "rgba(255,255,255,0.72)",
                backdropFilter: "blur(8px)",
                WebkitBackdropFilter: "blur(8px)",
                border: error ? "1px solid #ff4c49" : "1px solid rgba(255,255,255,0.6)",
              }}
            />
            {error && (
              <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#ff4c49] mb-2">{error}</p>
            )}

            <button
              onClick={handleRegister}
              className="w-full text-white rounded-[12px] py-3 mt-2 font-['Pretendard:SemiBold',sans-serif] text-[14px]"
              style={{
                background: "linear-gradient(135deg, #24C99A 0%, #14B989 100%)",
                boxShadow: "0 4px 16px rgba(34,197,154,0.30), inset 0 1px 0 rgba(255,255,255,0.25)",
              }}
            >
              등록하기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

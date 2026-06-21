import { useState } from "react";
import { Link } from "react-router";
import { X } from "lucide-react";
import acImage from "../../imports/제품페이지관리/47f735f974d0900368394246ff236d4a45df2a58.png";

const VALID_CODES: Record<string, { name: string; model: string }> = {
  "LG-WS-001": { name: "Living Room Air Conditioner", model: "LG Whisen Wall-mounted" },
  "LG-WS-002": { name: "Bedroom Air Conditioner", model: "LG Whisen Wall-mounted" },
  "LG-WS-003": { name: "Kitchen Air Conditioner", model: "LG Whisen Floor-standing" },
};

interface RegisteredDevice {
  id: string;
  code: string;
  name: string;
  model: string;
  status: string;
}

const initialDevices: RegisteredDevice[] = [
  { id: "1", code: "LG-WS-001", name: "Living Room Air Conditioner", model: "LG Whisen Wall-mounted", status: "Normal" },
  { id: "2", code: "LG-WS-002", name: "Bedroom Air Conditioner", model: "LG Whisen Wall-mounted", status: "Normal" },
];

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

const normalBadge = {
  background: "rgba(255,232,154,0.24)",
  border: "1px solid rgba(255,214,90,0.55)",
  color: "#D8A900",
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.68), 0 2px 8px rgba(255,214,90,0.18)",
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
    if (!matched) { setError("This product code is not valid."); return; }
    if (devices.some((d) => d.code === trimmed)) { setError("This product is already registered."); return; }
    setDevices((prev) => [...prev, { id: Date.now().toString(), code: trimmed, name: matched.name, model: matched.model, status: "Normal" }]);
    setCode("");
    setShowModal(false);
  };

  return (
    <div
      className="relative min-h-[calc(100vh-67px)] w-full overflow-hidden"
      style={{
        background:
          "radial-gradient(circle at -12% -8%, rgba(61,220,151,0.10) 0, rgba(61,220,151,0.06) 24%, transparent 48%), radial-gradient(circle at 112% 46%, rgba(100,210,190,0.09) 0, rgba(100,210,190,0.045) 28%, transparent 52%), linear-gradient(180deg, #f7f9f8 0%, #f7f9f8 100%)",
      }}
    >
      <div className="relative z-10 px-[18px] pt-[48px] pb-[12px] w-full max-w-[390px] mx-auto">
        <p className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-normal mb-[26px] pl-[2px]">
          My Devices
        </p>

        <div className="space-y-3">
          {devices.map((device) => (
            <Link key={device.id} to={`/device/${device.id}`} className="block">
              <div className="h-[104px] overflow-hidden rounded-[20px] px-[16px] py-[16px] flex items-center gap-[13px] transition-transform hover:scale-[1.01]" style={glass}>
                <div className="w-[70px] h-[70px] flex items-center justify-center flex-shrink-0">
                  <img src={acImage} alt="Air Conditioner" className="w-[66px] h-[66px] object-contain" />
                </div>
                <div className="min-w-0 flex-1 flex flex-col justify-center">
                  <p className="truncate font-['Pretendard:SemiBold',sans-serif] text-[15px] leading-[18px] text-[#111] mb-[2px]">{device.name}</p>
                  <p className="truncate font-['Pretendard:Regular',sans-serif] text-[12px] leading-[16px] text-[#888] mb-[8px]">{device.model}</p>
                  <span className="inline-flex h-[22px] min-w-[58px] w-fit items-center justify-center rounded-full px-[10px] font-['Pretendard:SemiBold',sans-serif] text-[10px]"
                    style={normalBadge}>
                    {device.status}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>

        <div className="mt-4 rounded-[20px] p-6 text-center" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-2">Register more products</p>
          <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888] mb-4">
            Enter a product code to receive personalized care services
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="text-white px-6 py-3 rounded-[12px] font-['Pretendard:Medium',sans-serif] text-[13px] transition-transform hover:scale-[1.01] active:scale-[0.99]"
            style={{
              background: "linear-gradient(135deg, #24C99A 0%, #14B989 100%)",
              boxShadow: "0 4px 16px rgba(34,197,154,0.30), inset 0 1px 0 rgba(255,255,255,0.25)",
            }}
          >
            Register with Product Code
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

            <p className="font-['Pretendard:SemiBold',sans-serif] text-[18px] text-[#111] mb-1">Enter Product Code</p>
            <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888] mb-4">
              Enter the product code printed on the box or the product body.
            </p>

            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. LG-WS-001"
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
              Register
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

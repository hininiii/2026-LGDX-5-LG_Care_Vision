import { useState } from "react";
import { useNavigate } from "react-router";
import { Eye, EyeOff } from "lucide-react";
import { loginUser } from "../api/user";
import { setCurrentUserEmail } from "../utils/authSession";

const airbrushBg = [
  "radial-gradient(ellipse 120% 55% at 50% -5%, rgba(255,190,140,0.22) 0%, transparent 70%)",
  "radial-gradient(ellipse 100% 50% at 50% 110%, rgba(100,220,185,0.18) 0%, transparent 70%)",
  "linear-gradient(180deg, #fffcf9 0%, #ffffff 50%, #f8fffc 100%)",
].join(", ");

const inputStyle = {
  background: "rgba(255,255,255,0.70)",
  backdropFilter: "blur(12px)",
  WebkitBackdropFilter: "blur(12px)",
  border: "1px solid rgba(220,220,200,0.60)",
  boxShadow: "0 2px 8px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.9)",
};

export function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!form.email || !form.password) {
      setError("Please enter your email and password.");
      return;
    }
    try {
      const response = await loginUser({ user_email: form.email, password: form.password });
      setCurrentUserEmail(response.user.user_email ?? form.email);
      localStorage.setItem("isLoggedIn", "true");
      const langSet = localStorage.getItem("appLanguage");
      if (!langSet) navigate("/setup/language");
      else navigate("/");
    } catch {
      setError("Please check your email or password.");
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="relative h-screen w-full max-w-[390px] overflow-y-auto" style={{ background: airbrushBg }}>

        <div className="relative z-10 px-[24px] pt-[80px] pb-[40px]">
          {/* 로고 */}
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[30px] text-[#ff4c49] mb-1">Care Vision</p>
          <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#888] mb-12">
            India Home Appliance Care and Service
          </p>

          <p className="font-['Pretendard:SemiBold',sans-serif] text-[24px] text-[#111] mb-6">Log In</p>

          <div className="flex flex-col gap-4 mb-6">
            <div>
              <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">Email</p>
              <input
                type="email"
                placeholder="Enter your email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-[16px] px-4 py-[14px] font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none transition-colors"
                style={inputStyle}
              />
            </div>
            <div>
              <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">Password</p>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  placeholder="Enter your password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full rounded-[16px] px-4 py-[14px] pr-12 font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none transition-colors"
                  style={inputStyle}
                />
                <button onClick={() => setShowPw(!showPw)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#c8ccd0]">
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
          </div>

          {error && <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#ff4c49] mb-4 ml-1">{error}</p>}

          <button
            onClick={handleSubmit}
            className="w-full text-white rounded-[20px] py-[16px] font-['Pretendard:SemiBold',sans-serif] text-[15px] mb-4 transition-opacity hover:opacity-90"
            style={{
              background: "linear-gradient(135deg, #ff6b35, #ff4c49)",
              boxShadow: "0 8px 24px rgba(255,76,73,0.30)",
            }}
          >
            Log In
          </button>

          <div className="flex items-center justify-center gap-2">
            <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">Don't have an account?</p>
            <button onClick={() => navigate("/signup")}
              className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#ff4c49]">
              Sign Up
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

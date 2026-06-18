import { useState } from "react";
import { useNavigate } from "react-router";
import { Eye, EyeOff } from "lucide-react";
import { registerUser } from "../api/user";
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

export function SignUp() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", phone: "", address: "", password: "", confirm: "" });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!form.name || !form.email || !form.phone || !form.address || !form.password || !form.confirm) {
      setError("Please fill in all fields.");
      return;
    }
    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }
    try {
      const response = await registerUser({
        user_email: form.email,
        password: form.password,
        name: form.name,
        phone: form.phone,
        address: form.address,
      });
      setCurrentUserEmail(response.user.user_email ?? form.email);
      localStorage.setItem("signedUp", "true");
      localStorage.setItem("careVisionShowWelcomeOnce", "true");
      localStorage.removeItem("appLanguage");
      navigate("/login");
    } catch {
      setError("Could not save your sign-up information.");
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="relative h-screen w-full max-w-[390px] overflow-y-auto" style={{ background: airbrushBg }}>

        <div className="relative z-10 px-[24px] pt-[56px] pb-[40px]">
          {/* 로고 */}
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[30px] text-[#ff4c49] mb-1">Care Vision</p>
          <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#888] mb-8">
            India Home Appliance Care and Service
          </p>

          <p className="font-['Pretendard:SemiBold',sans-serif] text-[24px] text-[#111] mb-6">Sign Up</p>

          <div className="flex flex-col gap-4 mb-6">
            {[
              { key: "name" as const, label: "Name", type: "text", placeholder: "Enter your name" },
              { key: "email" as const, label: "Email", type: "email", placeholder: "Enter your email" },
            ].map((f) => (
              <div key={f.key}>
                <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">{f.label}</p>
                <input
                  type={f.type}
                  placeholder={f.placeholder}
                  value={form[f.key]}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                  className="w-full rounded-[16px] px-4 py-[14px] font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none transition-colors"
                  style={inputStyle}
                />
              </div>
            ))}

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

            <div>
              <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">Confirm Password</p>
              <input
                type="password"
                placeholder="Re-enter your password"
                value={form.confirm}
                onChange={(e) => setForm({ ...form, confirm: e.target.value })}
                className="w-full rounded-[16px] px-4 py-[14px] font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none transition-colors"
                style={inputStyle}
              />
            </div>

            {[
              { key: "phone" as const, label: "Phone Number", type: "tel", placeholder: "Enter your phone number" },
              { key: "address" as const, label: "Address", type: "text", placeholder: "Enter your address" },
            ].map((f) => (
              <div key={f.key}>
                <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">{f.label}</p>
                <input
                  type={f.type}
                  placeholder={f.placeholder}
                  value={form[f.key]}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                  className="w-full rounded-[16px] px-4 py-[14px] font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none transition-colors"
                  style={inputStyle}
                />
              </div>
            ))}
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
            Sign Up
          </button>

          <div className="flex items-center justify-center gap-2">
            <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">Already have an account?</p>
            <button onClick={() => navigate("/login")}
              className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#ff4c49]">
              Log In
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

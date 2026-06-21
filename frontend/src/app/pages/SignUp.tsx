import { useState } from "react";
import { useNavigate } from "react-router";
import { Eye, EyeOff } from "lucide-react";
import careVisionLogo from "../../imports/care-vision-logo.svg";
import careVisionLogoIcon from "../../imports/care_vision_logo_icon.png";
import { registerUser } from "../api/user";
import { setCurrentUserEmail } from "../utils/authSession";

const airbrushBg = [
  "linear-gradient(160deg, #d6f2e8 0%, #f0f8e8 30%, #fce8f0 65%, #ede8f8 100%)",
].join(", ");

const inputStyle = {
  background: "rgba(255,255,255,0.70)",
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
  border: "1px solid rgba(255,255,255,0.85)",
  boxShadow: "0 2px 12px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.95)",
};

const cardStyle = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
  border: "1px solid rgba(255,255,255,0.85)",
  boxShadow: "0 8px 40px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

const primaryButtonStyle = {
  background: "linear-gradient(135deg, #3DDC97 0%, #14B989 100%)",
  boxShadow: "0 8px 24px rgba(29,184,122,0.32), inset 0 1px 0 rgba(255,255,255,0.25)",
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

        <div className="relative z-10 px-[28px] pt-[64px] pb-[48px]">
          {/* 로고 */}
          <div className="mb-[36px]">
            <div className="flex items-center gap-2 mb-3">
              <img
                src={careVisionLogoIcon}
                alt="Care Vision"
                className="w-9 h-9 rounded-[10px] object-cover"
                style={{ boxShadow: "0 4px 14px rgba(29,184,122,0.25)" }}
              />
              <img src={careVisionLogo} alt="Care Vision" className="h-[20px] w-[142px]" />
            </div>
            <p className="font-['Pretendard:Regular',sans-serif] text-[14px] text-[#888]">
              Create your account to start appliance care.
            </p>
          </div>

          <div className="rounded-[28px] p-6 mb-4" style={cardStyle}>
            <p className="font-['Pretendard:SemiBold',sans-serif] text-[16px] text-[#111] mb-5">Sign Up</p>

          <div className="flex flex-col gap-3 mb-2">
            {[
              { key: "name" as const, label: "Name", type: "text", placeholder: "Enter your name" },
              { key: "email" as const, label: "Email", type: "email", placeholder: "Enter your email" },
            ].map((f) => (
              <div key={f.key}>
                <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">{f.label}</p>
                <input
                  type={f.type}
                  placeholder={f.placeholder}
                  value={form[f.key]}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                  className="w-full rounded-[14px] px-4 py-[13px] font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none"
                  style={inputStyle}
                />
              </div>
            ))}

            <div>
              <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">Password</p>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  placeholder="Enter your password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full rounded-[14px] px-4 py-[13px] pr-12 font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none"
                  style={inputStyle}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#c8ccd0]"
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            <div>
              <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">Confirm Password</p>
              <input
                type="password"
                placeholder="Re-enter your password"
                value={form.confirm}
                onChange={(e) => setForm({ ...form, confirm: e.target.value })}
                className="w-full rounded-[14px] px-4 py-[13px] font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none"
                style={inputStyle}
              />
            </div>

            {[
              { key: "phone" as const, label: "Phone Number", type: "tel", placeholder: "Enter your phone number" },
              { key: "address" as const, label: "Address", type: "text", placeholder: "Enter your address" },
            ].map((f) => (
              <div key={f.key}>
                <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888] mb-1.5 ml-1">{f.label}</p>
                <input
                  type={f.type}
                  placeholder={f.placeholder}
                  value={form[f.key]}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                  className="w-full rounded-[14px] px-4 py-[13px] font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] placeholder:text-[#c8ccd0] outline-none"
                  style={inputStyle}
                />
              </div>
            ))}
          </div>

          {error && <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#ff4c49] mt-2 ml-1">{error}</p>}
          </div>

          <button
            onClick={handleSubmit}
            className="w-full text-white rounded-[18px] py-[15px] font-['Pretendard:Medium',sans-serif] text-[14px] mb-5 transition-opacity hover:opacity-90"
            style={primaryButtonStyle}
          >
            Sign Up
          </button>

          <div className="flex items-center justify-center gap-2">
            <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">Already have an account?</p>
            <button onClick={() => navigate("/login")}
              className="font-['Pretendard:SemiBold',sans-serif] text-[13px] text-[#14B989]">
              Log In
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

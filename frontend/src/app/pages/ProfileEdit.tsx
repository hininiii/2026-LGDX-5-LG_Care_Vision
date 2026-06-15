import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { ChevronLeft } from "lucide-react";
import { getUserProfile, updateUserProfile } from "../api/user";
import { getCurrentUserEmail, setCurrentUserEmail } from "../utils/authSession";

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

export function ProfileEdit() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: getCurrentUserEmail(),
    password: "",
    name: "",
    phone: "",
    address: "",
  });

  useEffect(() => {
    let active = true;
    async function loadProfile() {
      try {
        const profile = await getUserProfile();
        if (!active) return;
        setForm({
          email: profile.user_email ?? profile.email ?? getCurrentUserEmail(),
          password: "",
          name: profile.name,
          phone: profile.phone,
          address: profile.address,
        });
      } catch {
        // Keep current form values if the profile API is unavailable.
      }
    }
    loadProfile();
    return () => {
      active = false;
    };
  }, []);

  const update = (key: keyof typeof form, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const fields: { key: keyof typeof form; label: string; type?: string; placeholder?: string }[] = [
    { key: "email", label: "이메일", type: "email" },
    { key: "password", label: "비밀번호", type: "password", placeholder: "변경할 비밀번호" },
    { key: "name", label: "이름" },
    { key: "phone", label: "전화번호" },
    { key: "address", label: "주소" },
  ];

  return (
    <div className="relative min-h-full w-full bg-[#f7f9f8]">
      <div className="pointer-events-none absolute -top-20 -left-16 w-72 h-72 rounded-full"
        style={{ background: "rgba(61,220,151,0.09)", filter: "blur(90px)" }} />

      <div className="relative z-10 px-[18px] pt-[39px] pb-[20px] w-full max-w-[390px] mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => navigate("/settings")} className="p-1">
            <ChevronLeft size={24} className="text-[#555]" />
          </button>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[20px] tracking-[-0.3px] text-[#111]">
            개인정보 수정
          </p>
        </div>

        <div className="rounded-[20px] p-5 space-y-4 mb-4" style={glass}>
          {fields.map((f) => (
            <div key={f.key}>
              <p className="font-['Pretendard:Medium',sans-serif] text-[12px] text-[#888] mb-1.5">{f.label}</p>
              <input
                type={f.type ?? "text"}
                value={form[f.key]}
                placeholder={f.placeholder}
                onChange={(e) => update(f.key, e.target.value)}
                className="w-full rounded-[12px] px-4 py-3 font-['Pretendard:Regular',sans-serif] text-[14px] text-[#111] outline-none transition-colors"
                style={{
                  background: "rgba(255,255,255,0.65)",
                  border: "1px solid rgba(200,200,200,0.5)",
                }}
              />
            </div>
          ))}
        </div>

        <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888] mb-4 px-1">
          주소는 홈 화면 날씨 정보 기준 지역으로 사용됩니다.
        </p>

        <button
          onClick={() => {
            updateUserProfile({
              user_email: form.email,
              ...(form.password ? { password: form.password } : {}),
              name: form.name,
              phone: form.phone,
              address: form.address,
            }).then((response) => {
              setCurrentUserEmail(response.user.user_email ?? form.email);
              navigate("/settings");
            });
          }}
          className="w-full text-white rounded-[15px] py-4 font-['Pretendard:SemiBold',sans-serif] text-[15px]"
          style={{ background: "#FF6B6B" }}
        >
          저장
        </button>
      </div>
    </div>
  );
}

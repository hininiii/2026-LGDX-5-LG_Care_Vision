import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { ChevronRight, User, Globe, LogOut } from "lucide-react";
import { getUserProfile } from "../api/user";
import type { UserProfile } from "../types/user";

const settingsItems = [
  { to: "/settings/profile", icon: User, label: "Edit Profile", description: "Name, email, password, phone number, address" },
  { to: "/settings/language", icon: Globe, label: "Language Settings", description: "Service display language" },
];

const glass = {
  background: "rgba(255,255,255,0.55)",
  backdropFilter: "blur(28px)",
  WebkitBackdropFilter: "blur(28px)",
  border: "1px solid rgba(255,255,255,0.80)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.95)",
};

export function Settings() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    let active = true;
    async function loadProfile() {
      try {
        const userProfile = await getUserProfile();
        if (active) setProfile(userProfile);
      } catch (error) {
        console.error("Failed to load settings profile", error);
      }
    }
    loadProfile();
    return () => {
      active = false;
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("isLoggedIn");
    navigate("/welcome");
  };

  const displayName = profile?.name || "User";
  const displayEmail = profile?.user_email || profile?.email || "";
  const initial = displayName.trim().charAt(0).toUpperCase() || "U";

  return (
    <div className="relative min-h-full w-full bg-[#f7f9f8]">
      <div className="pointer-events-none absolute -top-20 -left-16 w-72 h-72 rounded-full"
        style={{ background: "rgba(61,220,151,0.09)", filter: "blur(90px)" }} />

      <div className="relative z-10 px-[18px] pt-[48px] pb-[20px] w-full max-w-[390px] mx-auto">
        <p className="font-['Pretendard:Medium',sans-serif] text-[20px] tracking-[-0.3px] text-black leading-normal mb-[26px] pl-[2px]">
          Settings
        </p>

        {/* Usage자 정보 */}
        <div className="rounded-[20px] p-5 mb-4" style={glass}>
          <div className="flex items-center gap-4">
            <div className="w-[56px] h-[56px] rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: "linear-gradient(135deg, #1DB87A, #3DDC97)" }}>
              <p className="font-['Pretendard:Bold',sans-serif] text-[22px] text-white">{initial}</p>
            </div>
            <div>
              <p className="font-['Pretendard:SemiBold',sans-serif] text-[18px] text-[#111] mb-[2px]">{displayName}</p>
              <p className="font-['Pretendard:Regular',sans-serif] text-[13px] text-[#888]">{displayEmail}</p>
            </div>
          </div>
        </div>

        {/* Settings 메뉴 */}
        <div className="rounded-[20px] overflow-hidden mb-4" style={glass}>
          {settingsItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <div key={index}>
                <Link to={item.to} className="w-full px-5 py-4 flex items-center gap-4 hover:bg-white/30 transition-colors">
                  <div className="w-[38px] h-[38px] rounded-[12px] flex items-center justify-center flex-shrink-0"
                    style={{ background: "rgba(61,220,151,0.10)", border: "1px solid rgba(29,184,122,0.20)" }}>
                    <Icon size={18} className="text-[#1DB87A]" />
                  </div>
                  <div className="flex-1 text-left">
                    <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-[2px]">{item.label}</p>
                    <p className="font-['Pretendard:Regular',sans-serif] text-[12px] text-[#888]">{item.description}</p>
                  </div>
                  <ChevronRight size={18} className="text-[#bbb]" />
                </Link>
                {index < settingsItems.length - 1 && (
                  <div className="h-[1px] mx-5" style={{ background: "rgba(200,200,200,0.3)" }} />
                )}
              </div>
            );
          })}
        </div>

        {/* App Info */}
        <div className="rounded-[20px] p-5 mb-4" style={glass}>
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#111] mb-3">App Info</p>
          <div className="flex justify-between">
            <p className="font-['Pretendard:Regular',sans-serif] text-[14px] text-[#888]">LG_DX_2TEAM</p>
            <p className="font-['Pretendard:Medium',sans-serif] text-[14px] text-[#111]">26.06.22</p>
          </div>
        </div>

        {/* Log Out */}
        <button onClick={handleLogout} className="w-full rounded-[20px] p-4 flex items-center justify-center gap-2 hover:bg-white/40 transition-colors" style={glass}>
          <LogOut size={18} className="text-[#ff4c49]" />
          <p className="font-['Pretendard:SemiBold',sans-serif] text-[15px] text-[#ff4c49]">Log Out</p>
        </button>
      </div>
    </div>
  );
}

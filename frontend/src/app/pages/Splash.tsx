import { useEffect } from "react";
import { useNavigate } from "react-router";
import { motion } from "motion/react";
import careVisionLogo from "../../imports/care-vision-logo.svg";

const pageBackground =
  "linear-gradient(160deg, #d6f2e8 0%, #f0f8e8 30%, #fce8f0 65%, #ede8f8 100%)";

export function Splash() {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = window.setTimeout(() => navigate("/", { replace: true }), 2200);
    return () => window.clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div
        className="relative h-screen w-full max-w-[390px] overflow-hidden flex flex-col items-center justify-center px-[28px]"
        style={{ background: pageBackground }}
      >
        <div className="flex flex-col items-center gap-6">
          <motion.img
            src={careVisionLogo}
            alt="Care Vision"
            className="w-[210px] h-auto"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.55, ease: [0.34, 1.15, 0.64, 1] }}
          />

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45, duration: 0.45, ease: [0.34, 1.1, 0.64, 1] }}
            className="flex flex-col items-center gap-2 text-center"
          >
            <p className="font-['Pretendard:Medium',sans-serif] text-[15px] text-[#666] leading-[1.5]">
              Care Vision protects your precious time.
            </p>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="absolute bottom-[60px] flex gap-[6px]"
        >
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-[6px] h-[6px] rounded-full"
              style={{ background: "#3DDC97" }}
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </motion.div>
      </div>
    </div>
  );
}

import { Outlet, Navigate, useLocation, useNavigate } from "react-router";
import { NavigationBar } from "./NavigationBar";
import { AnimatePresence, motion } from "motion/react";
import chatbotGif from "../../imports/LG______.gif";

export function Layout() {
  const isLoggedIn = localStorage.getItem("isLoggedIn");
  const location = useLocation();
  const navigate = useNavigate();
  const isSelfCareRoute = location.pathname === "/self-care";
  const isHomeRoute = location.pathname === "/";

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="relative h-screen w-full max-w-[390px] overflow-hidden bg-[#f7f9f8]">
        <div className="relative h-[calc(100vh-67px)] overflow-x-hidden overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={isSelfCareRoute ? { opacity: 1, y: 4, filter: "blur(4px)" } : { opacity: 0, filter: "blur(0px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0 }}
              transition={{
                delay: isSelfCareRoute ? 0.04 : 0,
                duration: isSelfCareRoute ? 0.36 : 0.32,
                ease: [0.22, 1, 0.36, 1],
              }}
              style={{ position: "relative" }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
        {isHomeRoute && (
          <button
            onClick={() => navigate("/chat")}
            className="absolute right-[18px] bottom-[124px] z-50 p-0"
            aria-label="Open chatbot"
          >
            <img
              src={chatbotGif}
              alt="Chatbot"
              className="h-[78px] w-[78px] rounded-full cursor-pointer drop-shadow-lg transition-transform hover:scale-110"
            />
          </button>
        )}
        <NavigationBar />
      </div>
    </div>
  );
}

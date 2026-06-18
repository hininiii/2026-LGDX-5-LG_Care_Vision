import { Outlet, Navigate, useLocation } from "react-router";
import { NavigationBar } from "./NavigationBar";
import { AnimatePresence, motion } from "motion/react";

export function Layout() {
  const isLoggedIn = localStorage.getItem("isLoggedIn");
  const location = useLocation();
  const isSelfCareRoute = location.pathname === "/self-care";

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="relative h-screen w-full max-w-[390px] overflow-hidden bg-[#f7f9f8]">
        <div className="relative h-[calc(100vh-67px)] overflow-x-hidden overflow-y-auto">
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
        <NavigationBar />
      </div>
    </div>
  );
}

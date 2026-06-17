import { Outlet, Navigate, useLocation } from "react-router";
import { NavigationBar } from "./NavigationBar";
import { AnimatePresence, motion } from "motion/react";

export function Layout() {
  const isLoggedIn = localStorage.getItem("isLoggedIn");
  const location = useLocation();

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="relative h-screen w-full max-w-[390px] overflow-hidden bg-[#f7f9f8]">
        <div className="relative h-[calc(100vh-67px)] overflow-y-auto">
          <AnimatePresence>
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
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

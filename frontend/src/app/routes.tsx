import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { Home } from "./pages/Home";
import { Device } from "./pages/Device";
import { Chat } from "./pages/Chat";
import { Settings } from "./pages/Settings";
import { DeviceDetail } from "./pages/DeviceDetail";
import { SelfCare } from "./pages/SelfCare";
import { ARGuide } from "./pages/ARGuide";
import { ProfileEdit } from "./pages/ProfileEdit";
import { LanguageSettings } from "./pages/LanguageSettings";
import { Login } from "./pages/Login";
import { SignUp } from "./pages/SignUp";
import { InitialLanguage } from "./pages/InitialLanguage";

export const router = createBrowserRouter([
  { path: "/signup", Component: SignUp },
  { path: "/login", Component: Login },
  { path: "/setup/language", Component: InitialLanguage },
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: Home },
      { path: "device", Component: Device },
      { path: "device/:id", Component: DeviceDetail },
      { path: "self-care", Component: SelfCare },
      { path: "settings", Component: Settings },
      { path: "settings/profile", Component: ProfileEdit },
      { path: "settings/language", Component: LanguageSettings },
    ],
  },
  {
    path: "/ar-guide",
    element: (
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <div className="relative h-screen w-full max-w-[390px] overflow-hidden">
          <ARGuide />
        </div>
      </div>
    ),
  },
  {
    path: "/chat",
    element: (
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <div className="relative h-screen w-full max-w-[390px] overflow-hidden">
          <Chat />
        </div>
      </div>
    ),
  },
]);

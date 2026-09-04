import { useState } from "react";
import { AdminSessionProvider, useAdminSession } from "./context/AdminSessionContext";
import BackgroundVines from "./components/BackgroundVines";
import { ToastProvider } from "./components/Toast";
import PunchClockView from "./views/PunchClockView";
import AdminLoginView from "./views/AdminLoginView";
import AdminRecoverView from "./views/AdminRecoverView";
import AdminDashboard from "./views/admin/AdminDashboard";
import type { View } from "./types";

function AppShell() {
  const [view, setView] = useState<View>("clock");
  const { setPass } = useAdminSession();

  return (
    <>
      <BackgroundVines />
      <div id="app-root">
      {view === "clock" && <PunchClockView onGoAdmin={() => setView("admin-login")} />}
      {view === "admin-login" && (
        <AdminLoginView
          onCancel={() => setView("clock")}
          onForgot={() => setView("admin-recover")}
          onLoggedIn={(password) => {
            setPass(password);
            setView("admin");
          }}
        />
      )}
      {view === "admin-recover" && (
        <AdminRecoverView onDone={() => setView("admin-login")} onCancel={() => setView("admin-login")} />
      )}
      {view === "admin" && <AdminDashboard onExit={() => setView("clock")} />}
      </div>
    </>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AdminSessionProvider>
        <AppShell />
      </AdminSessionProvider>
    </ToastProvider>
  );
}

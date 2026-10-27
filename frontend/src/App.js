import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Show } from "@clerk/react";
import { SignInForm, SignUpForm } from "@/components/auth/AuthForms";
import { Toaster } from "sonner";
import ClerkAuthProvider from "@/components/auth/ClerkAuthProvider";
import { MeProvider } from "@/lib/api";
import Shell from "@/components/civic/Shell";
import Dashboard from "@/pages/Dashboard";
import Projects from "@/pages/Projects";
import ProjectDetail from "@/pages/ProjectDetail";
import RecordsPage from "@/pages/RecordsPage";
import Team from "@/pages/Team";
import Assistant from "@/pages/Assistant";
import More from "@/pages/More";
import { PwaProvider } from "@/components/mobile/PwaProvider";
import { InstallControl } from "@/components/mobile/InstallPanel";
import "@/App.css";
import "@/civic.css";
import "@/mobile.css";

function AuthGate({ children }) {
  return <><Show when="signed-in">{children}</Show><Show when="signed-out"><Navigate to="/sign-in" replace /></Show></>;
}

function AuthPages() {
  const signup = useLocation().pathname.startsWith("/sign-up");
  return <><Show when="signed-in"><Navigate to="/" replace /></Show><Show when="signed-out"><div className="auth-page"><div className="auth-aside"><div className="auth-brand" data-testid="auth-brand"><span className="brand-mark">CP</span><div><strong>CIVICPRO</strong><small>FIELD COMMAND</small></div></div><p>{signup ? "One team. Every site. In sync." : "Your site. Your team. In your pocket."}</p><span>CONSTRUCTION PROJECT WORKSPACE</span></div>
    <div className="auth-stack">{signup ? <SignUpForm /> : <SignInForm />}<InstallControl testid="auth-install-button" /></div></div></Show></>;
}

export default function App() {
  return <BrowserRouter><PwaProvider><ClerkAuthProvider><Toaster position="top-right" richColors closeButton />
    <Routes>
      <Route path="/sign-in/*" element={<AuthPages />} />
      <Route path="/sign-up/*" element={<AuthPages />} />
      <Route element={<AuthGate><MeProvider><Shell /></MeProvider></AuthGate>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/reports" element={<RecordsPage key="reports" type="reports" />} />
        <Route path="/issues" element={<RecordsPage key="issues" type="issues" />} />
        <Route path="/team" element={<Team />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/more" element={<More />} />
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes></ClerkAuthProvider></PwaProvider></BrowserRouter>;
}

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
import "@/App.css";
import "@/civic.css";

function AuthGate({ children }) {
  return <><Show when="signed-in">{children}</Show><Show when="signed-out"><Navigate to="/sign-in" replace /></Show></>;
}

function AuthPages() {
  const signup = useLocation().pathname.startsWith("/sign-up");
  return <div className="auth-page"><div className="auth-aside"><span className="brand-mark">CP</span><p>{signup ? "Bring every site update into one clear command center." : "Field intelligence for projects that move the city forward."}</p>{!signup && <span>Secure project workspace</span>}</div>
    {signup ? <SignUpForm /> : <SignInForm />}</div>;
}

export default function App() {
  return <BrowserRouter><ClerkAuthProvider><Toaster position="top-right" richColors closeButton />
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
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes></ClerkAuthProvider></BrowserRouter>;
}

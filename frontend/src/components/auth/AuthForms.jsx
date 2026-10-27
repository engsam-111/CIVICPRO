import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useSignIn, useSignUp } from "@clerk/react";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";

const msg = (e, fallback) => e?.errors?.[0]?.longMessage || e?.errors?.[0]?.message || e?.longMessage || e?.message || fallback;

function AuthInput({ name, label, type = "text", value, onChange, icon: Icon, autoComplete, minLength, inputMode, maxLength }) {
  const [show, setShow] = useState(false);
  const pw = type === "password";
  return <label className="auth-field"><span>{label}</span><div className="auth-input">{Icon && <Icon size={16} />}
    <input name={name} type={pw && show ? "text" : type} value={value} onChange={e => onChange(e.target.value)} required autoComplete={autoComplete} minLength={minLength} inputMode={inputMode} maxLength={maxLength} data-testid={`auth-${name}-input`} />
    {pw && <button type="button" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"} data-testid={`auth-${name}-toggle`}>{show ? <EyeOff size={16} /> : <Eye size={16} />}</button>}</div></label>;
}

function CodeStep({ email, onVerify, onResend, busy, error }) {
  const [code, setCode] = useState("");
  const [resendError, setResendError] = useState("");
  const [resent, setResent] = useState(false);
  const resend = async () => { setResendError(""); setResent(false); try { const result = await onResend(); if (result?.error) throw result.error; setResent(true); } catch (err) { setResendError(msg(err, "Could not resend the code. Try again.")); } };
  return <form className="auth-form" onSubmit={e => { e.preventDefault(); onVerify(code); }} data-testid="auth-code-form">
    <h2>Check your email</h2><p className="auth-sub">We sent a 6-digit code to <b>{email}</b>.</p>
    <AuthInput name="code" label="Verification code" value={code} onChange={value => setCode(value.replace(/\D/g, ""))} autoComplete="one-time-code" inputMode="numeric" maxLength={6} />
    {error && <p className="auth-error" role="alert" data-testid="auth-error">{error}</p>}
    <button className="primary-btn auth-submit" disabled={busy || code.length < 6} data-testid="auth-verify-button">{busy ? "Verifying…" : "Verify and continue"}</button>
    {resendError && <p className="auth-error" role="alert" data-testid="auth-resend-error">{resendError}</p>}
    {resent && <p className="auth-note" role="status" data-testid="auth-code-resent">A new code has been sent.</p>}
    <button type="button" className="text-btn" onClick={resend} disabled={busy} data-testid="auth-resend-button">Resend code</button>
  </form>;
}

export function SignInForm() {
  const { signIn, fetchStatus } = useSignIn();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState("password");
  const [error, setError] = useState("");
  const busy = fetchStatus === "fetching";
  const done = async () => { const r = await signIn.finalize(); if (r?.error) throw r.error; navigate("/", { replace: true }); };
  const submit = async e => {
    e.preventDefault(); setError("");
    try {
      const r = await signIn.password({ emailAddress: email.trim(), password });
      if (r.error) throw r.error;
      if (signIn.status === "complete") return await done();
      if (signIn.status === "needs_second_factor" || signIn.status === "needs_client_trust") {
        const s = await signIn.mfa.sendEmailCode(); if (s.error) throw s.error; return setStep("code");
      }
      if (signIn.status === "needs_new_password") return setError("Your password needs to be changed. Ask your project manager to reset it for you.");
      setError("This sign-in needs an extra step that isn't supported here. Contact your manager.");
    } catch (err) { setError(msg(err, "Email or password is incorrect")); }
  };
  const verify = async code => {
    setError("");
    try { const r = await signIn.mfa.verifyEmailCode({ code }); if (r.error) throw r.error; if (signIn.status === "complete") return await done(); setError("Verification incomplete, please try again."); }
    catch (err) { setError(msg(err, "That code didn't work")); }
  };
  if (step === "code") return <CodeStep email={email} onVerify={verify} onResend={() => signIn.mfa.sendEmailCode()} busy={busy} error={error} />;
  return <form className="auth-form" onSubmit={submit} data-testid="sign-in-form">
    <h2>Sign in</h2><p className="auth-sub">Use your work email and password.</p>
    <AuthInput name="email" label="Email" type="email" value={email} onChange={setEmail} icon={Mail} autoComplete="email" />
    <AuthInput name="password" label="Password" type="password" value={password} onChange={setPassword} icon={Lock} autoComplete="current-password" />
    {error && <p className="auth-error" role="alert" data-testid="auth-error">{error}</p>}
    <button className="primary-btn auth-submit" disabled={busy} data-testid="sign-in-submit-button">{busy ? "Signing in…" : "Sign in"}</button>
    <p className="auth-note" data-testid="forgot-password-note">Forgot your password? Ask your project manager to reset it.</p>
    <p className="auth-switch">New to the team? <Link to="/sign-up" data-testid="go-to-sign-up">Create an account</Link></p>
  </form>;
}

export function SignUpForm() {
  const { signUp, fetchStatus } = useSignUp();
  const navigate = useNavigate();
  const [f, setF] = useState({ firstName: "", lastName: "", email: "", password: "" });
  const [step, setStep] = useState("details");
  const [error, setError] = useState("");
  const busy = fetchStatus === "fetching";
  const set = k => v => setF(x => ({ ...x, [k]: v }));
  const submit = async e => {
    e.preventDefault(); setError("");
    try {
      let r = await signUp.password({ emailAddress: f.email.trim(), password: f.password, firstName: f.firstName.trim(), lastName: f.lastName.trim() });
      if (r.error) throw r.error;
      r = await signUp.verifications.sendEmailCode(); if (r.error) throw r.error;
      setStep("code");
    } catch (err) { setError(msg(err, "Could not create your account")); }
  };
  const verify = async code => {
    setError("");
    try {
      const r = await signUp.verifications.verifyEmailCode({ code }); if (r.error) throw r.error;
      if (signUp.status !== "complete") return setError("Some details are still missing. Please try again.");
      const fin = await signUp.finalize(); if (fin?.error) throw fin.error;
      navigate("/", { replace: true });
    } catch (err) { setError(msg(err, "That code didn't work")); }
  };
  if (step === "code") return <CodeStep email={f.email} onVerify={verify} onResend={() => signUp.verifications.sendEmailCode()} busy={busy} error={error} />;
  return <form className="auth-form" onSubmit={submit} data-testid="sign-up-form">
    <h2>Create your account</h2><p className="auth-sub">A manager approves new members before they can see project data.</p>
    <div className="auth-row"><AuthInput name="firstName" label="First name" value={f.firstName} onChange={set("firstName")} autoComplete="given-name" /><AuthInput name="lastName" label="Last name" value={f.lastName} onChange={set("lastName")} autoComplete="family-name" /></div>
    <AuthInput name="email" label="Work email" type="email" value={f.email} onChange={set("email")} icon={Mail} autoComplete="email" />
    <AuthInput name="password" label="Password (min. 8 characters)" type="password" value={f.password} onChange={set("password")} icon={Lock} autoComplete="new-password" minLength={8} />
    <div id="clerk-captcha" />
    {error && <p className="auth-error" role="alert" data-testid="auth-error">{error}</p>}
    <button className="primary-btn auth-submit" disabled={busy} data-testid="sign-up-submit-button">{busy ? "Creating account…" : "Create account"}</button>
    <p className="auth-switch">Already have an account? <Link to="/sign-in" data-testid="go-to-sign-in">Sign in</Link></p>
  </form>;
}

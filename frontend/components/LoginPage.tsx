"use client";
import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import styles from "./LoginPage.module.css";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    const result = await signIn("credentials", {
      username,
      password,
      redirect: false,
    });
    setLoading(false);
    if (result?.ok) {
      router.push("/");
    } else {
      setError("Invalid username or password.");
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.backgroundOrbs}>
        <div className={styles.orb1} />
        <div className={styles.orb2} />
        <div className={styles.orb3} />
      </div>

      <div className={styles.card}>
        <div className={styles.logoArea}>
          <div className={styles.logoIcon}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="url(#g1)" />
              <path d="M2 17l10 5 10-5" stroke="url(#g1)" strokeWidth="2" strokeLinecap="round" />
              <path d="M2 12l10 5 10-5" stroke="url(#g1)" strokeWidth="2" strokeLinecap="round" />
              <defs>
                <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#6382ff" />
                  <stop offset="100%" stopColor="#a78bfa" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 className={styles.title}>
            Amazon Bot <span className="gradient-text">Assistant</span>
          </h1>
          <p className={styles.subtitle}>
            AI-powered customer support with human-in-the-loop escalation
          </p>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label htmlFor="username" className={styles.label}>Username</label>
            <input
              id="username"
              type="text"
              className="input"
              placeholder="demo"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="password" className={styles.label}>Password</label>
            <input
              id="password"
              type="password"
              className="input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button
            id="login-btn"
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center" }}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className={styles.spinner} />
                Signing in…
              </>
            ) : (
              "Sign In →"
            )}
          </button>

          <p className={styles.hint}>
            Demo credentials: <code>demo</code> / <code>password</code>
          </p>
        </form>
      </div>
    </div>
  );
}

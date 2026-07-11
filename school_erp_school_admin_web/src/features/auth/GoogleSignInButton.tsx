import { useEffect, useRef, useState } from "react";

// Minimal typings for the Google Identity Services global. We load the
// script in index.html; here we just read window.google.accounts.id.
interface GoogleCredentialResponse {
  credential: string; // the ID token (JWT)
}
interface GoogleIdApi {
  initialize: (cfg: {
    client_id: string;
    callback: (r: GoogleCredentialResponse) => void;
  }) => void;
  renderButton: (parent: HTMLElement, opts: Record<string, unknown>) => void;
}
declare global {
  interface Window {
    google?: { accounts?: { id?: GoogleIdApi } };
  }
}

// Web OAuth client ID. Prefer the build-time env var, but fall back to
// the known web client so the button shows even when the deploy env
// didn't set VITE_GOOGLE_CLIENT_ID_WEB. Client IDs are public (they're
// embedded in every shipped bundle), so hardcoding a fallback is safe.
const CLIENT_ID =
  (import.meta.env.VITE_GOOGLE_CLIENT_ID_WEB as string | undefined) ||
  "158812707380-i6f00ih0imbt2dh75s9dr849481joqap.apps.googleusercontent.com";

/** Renders Google's official "Sign in with Google" button. On success
 * it calls onCredential with the ID token, which the caller trades for
 * our own session via POST /v1/auth/google. Renders nothing if the
 * client ID isn't configured. */
export function GoogleSignInButton({
  onCredential,
  disabled,
}: {
  onCredential: (idToken: string) => void;
  disabled?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!CLIENT_ID) return;
    // The GSI script loads async; poll briefly until it's on window.
    let tries = 0;
    const t = setInterval(() => {
      tries += 1;
      const id = window.google?.accounts?.id;
      if (id && ref.current) {
        clearInterval(t);
        id.initialize({
          client_id: CLIENT_ID,
          callback: (r) => {
            if (r?.credential) onCredential(r.credential);
          },
        });
        id.renderButton(ref.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "signin_with",
          shape: "rectangular",
          logo_alignment: "left",
          width: 320,
        });
        setReady(true);
      } else if (tries > 40) {
        clearInterval(t); // give up after ~10s
      }
    }, 250);
    return () => clearInterval(t);
    // onCredential is stable enough for our use; re-running would
    // re-render the button.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!CLIENT_ID) return null;

  return (
    <div className={disabled ? "pointer-events-none opacity-50" : ""}>
      <div ref={ref} />
      {!ready && (
        <p className="text-xs text-muted-foreground">Loading Google…</p>
      )}
    </div>
  );
}

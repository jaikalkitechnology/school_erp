import { useEffect, useState, type ReactNode } from "react";
import { api } from "@/lib/api";

/** Blob URLs for uploaded logos, keyed by stored path, so the sidebar and
 *  settings preview don't download the same file twice. */
const blobCache = new Map<string, string>();

const isDirectUrl = (u: string) => /^(https?:|data:|blob:)/i.test(u);

/** Resolves a logo `src` to something an <img> or <link> can use. Paths
 *  from /v1/uploads need the login token, so they're fetched as a blob. */
async function loadLogo(src: string): Promise<string> {
  if (isDirectUrl(src)) return src;
  const hit = blobCache.get(src);
  if (hit) return hit;
  const res = await api.get<Blob>(`/v1/uploads/${src}`, { responseType: "blob" });
  const u = URL.createObjectURL(res.data);
  blobCache.set(src, u);
  return u;
}

/** Shows the school logo. `src` is either a web URL or a path from
 *  /v1/uploads. Renders `fallback` while there's no logo or it fails to load. */
export function SchoolLogo({
  src, alt, className, fallback = null,
}: {
  src: string | null | undefined;
  alt: string;
  className?: string;
  fallback?: ReactNode;
}) {
  const initial = !src ? null : isDirectUrl(src) ? src : blobCache.get(src) ?? null;
  const [url, setUrl] = useState<string | null>(initial);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
    if (!src) {
      setUrl(null);
      return;
    }
    setUrl(isDirectUrl(src) ? src : blobCache.get(src) ?? null);
    let cancelled = false;
    loadLogo(src)
      .then((u) => {
        if (!cancelled) setUrl(u);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [src]);

  if (!url || failed) return <>{fallback}</>;
  return <img src={url} alt={alt} className={className} onError={() => setFailed(true)} />;
}

/** The Jaikalki icon, shown wherever a school has no logo yet. */
export function JaikalkiIcon({ className }: { className?: string }) {
  return <img src="/favicon-192.png" alt="Jaikalki" className={className} />;
}

/** Puts the school's logo in the browser tab while signed in, and restores
 *  the Jaikalki favicons from index.html when there's none or on sign-out. */
export function useSchoolFavicon(src: string | null | undefined) {
  useEffect(() => {
    if (!src) return;
    const links = Array.from(document.querySelectorAll<HTMLLinkElement>("link[rel='icon']"));
    const original = links.map((l) => ({ href: l.getAttribute("href"), type: l.getAttribute("type") }));
    let cancelled = false;
    loadLogo(src)
      .then((u) => {
        if (cancelled) return;
        for (const l of links) {
          l.removeAttribute("type"); // the logo may be PNG, JPG or SVG
          l.href = u;
        }
      })
      .catch(() => {
        // keep the Jaikalki icon
      });
    return () => {
      cancelled = true;
      links.forEach((l, i) => {
        const o = original[i];
        if (o.href) l.setAttribute("href", o.href);
        if (o.type) l.setAttribute("type", o.type);
      });
    };
  }, [src]);
}

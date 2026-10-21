import { useEffect, useState, type ReactNode } from "react";
import { api } from "@/lib/api";

/** Blob URLs for uploaded logos, keyed by stored path, so the sidebar and
 *  settings preview don't download the same file twice. */
const blobCache = new Map<string, string>();

const isDirectUrl = (u: string) => /^(https?:|data:|blob:)/i.test(u);

/** Shows the school logo. `src` is either a web URL or a path from
 *  /v1/uploads (which needs the login token, so it's fetched as a blob).
 *  Renders `fallback` while there's no logo or it fails to load. */
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
    if (isDirectUrl(src)) {
      setUrl(src);
      return;
    }
    const hit = blobCache.get(src);
    if (hit) {
      setUrl(hit);
      return;
    }
    setUrl(null);
    let cancelled = false;
    api
      .get<Blob>(`/v1/uploads/${src}`, { responseType: "blob" })
      .then((res) => {
        const u = URL.createObjectURL(res.data);
        blobCache.set(src, u);
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

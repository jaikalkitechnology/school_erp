import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Inflight blob-URL cache so a 20-row table doesn't refetch the same
 *  photo twice when React re-renders. Keyed by the relative path the
 *  backend stored (tenant_X/students/photos/abc.jpg). */
const photoCache = new Map<string, string>();

interface Props {
  photoUrl: string | null;
  name: string;
  size?: number;
  className?: string;
}

export function StudentAvatar({ photoUrl, name, size = 36, className }: Props) {
  const [blob, setBlob] = useState<string | null>(
    photoUrl ? photoCache.get(photoUrl) ?? null : null,
  );

  useEffect(() => {
    if (!photoUrl) {
      setBlob(null);
      return;
    }
    const cached = photoCache.get(photoUrl);
    if (cached) {
      setBlob(cached);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get<Blob>(`/v1/uploads/${photoUrl}`, {
          responseType: "blob",
        });
        const url = URL.createObjectURL(res.data);
        photoCache.set(photoUrl, url);
        if (!cancelled) setBlob(url);
      } catch {
        if (!cancelled) setBlob(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [photoUrl]);

  const initials = (() => {
    const parts = name.trim().split(/\s+/);
    if (!parts.length || !parts[0]) return "?";
    if (parts.length === 1) return parts[0][0].toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  })();

  return (
    <div
      style={{ width: size, height: size }}
      className={cn(
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-saffron-pale text-[11px] font-bold text-indigo-dark",
        className,
      )}
      title={name}
    >
      {blob ? (
        <img
          src={blob}
          alt={name}
          className="h-full w-full object-cover"
        />
      ) : (
        <span>{initials}</span>
      )}
    </div>
  );
}

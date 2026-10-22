import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchTenantLogo, uploadTenantLogo } from "./api";
import type { Tenant } from "./types";

const MAX_MB = 10;
const OK_TYPES = ["image/png", "image/jpeg", "image/svg+xml"];
const OK_EXT = /\.(png|jpe?g|svg)$/i;

function initials(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean);
  return ((words[0]?.[0] ?? "") + (words[1]?.[0] ?? "")).toUpperCase() || "?";
}

/** The school's profile image (logo), or its initials when it has none.
 *  With `editable`, clicking it picks a new image and uploads it. */
export function SchoolAvatar({
  tenant,
  editable = false,
  size = 40,
}: {
  tenant: Tenant;
  editable?: boolean;
  size?: number;
}) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const logo = useQuery({
    queryKey: ["tenant-logo", tenant.id, tenant.logo_url],
    queryFn: () => fetchTenantLogo(tenant.id),
    enabled: !!tenant.logo_url,
    staleTime: Infinity,
    retry: false,
  });

  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    if (!logo.data) {
      setSrc(null);
      return;
    }
    const url = URL.createObjectURL(logo.data);
    setSrc(url);
    return () => URL.revokeObjectURL(url);
  }, [logo.data]);

  const upload = useMutation({
    mutationFn: (file: File) => uploadTenantLogo(tenant.id, file),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["tenants"] });
      queryClient.invalidateQueries({ queryKey: ["tenant", tenant.id] });
    },
    onError: () => setError("Upload failed"),
  });

  const onPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!OK_TYPES.includes(file.type) && !OK_EXT.test(file.name)) {
      setError("Use PNG, JPG or SVG");
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`Max ${MAX_MB} MB`);
      return;
    }
    upload.mutate(file);
  };

  const face = (
    <span
      className="relative flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-saffron-pale bg-white font-display font-semibold text-warm-white"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        backgroundColor: src ? undefined : tenant.primary_color || "#E8590C",
      }}
    >
      {src ? (
        <img src={src} alt={`${tenant.school_name} logo`} className="h-full w-full object-contain" />
      ) : (
        initials(tenant.school_name)
      )}
      {upload.isPending && (
        <span className="absolute inset-0 flex items-center justify-center bg-black/40">
          <Loader2 className="h-4 w-4 animate-spin text-white" />
        </span>
      )}
    </span>
  );

  if (!editable) return face;

  return (
    <span className="relative inline-flex flex-col items-center">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={upload.isPending}
        title={src ? "Change profile image" : "Add profile image"}
        aria-label={src ? "Change profile image" : "Add profile image"}
        className={cn("group relative rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-saffron")}
      >
        {face}
        <span className="absolute -bottom-0.5 -right-0.5 flex h-5 w-5 items-center justify-center rounded-full border-2 border-white bg-saffron text-white shadow transition-transform group-hover:scale-110">
          <Camera className="h-2.5 w-2.5" />
        </span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,.png,.jpg,.jpeg,.svg"
        className="hidden"
        onChange={onPick}
        data-testid={`logo-input-${tenant.id}`}
      />
      {error && (
        <span className="absolute top-full mt-0.5 whitespace-nowrap text-[10px] font-medium text-destructive">
          {error}
        </span>
      )}
    </span>
  );
}

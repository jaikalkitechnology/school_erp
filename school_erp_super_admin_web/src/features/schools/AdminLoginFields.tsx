import { useState } from "react";
import { Eye, EyeOff, Wand2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface AdminLoginForm {
  full_name: string;
  email: string;
  password: string;
  confirm: string;
}

export const EMPTY_ADMIN_LOGIN: AdminLoginForm = { full_name: "", email: "", password: "", confirm: "" };

const EMAIL = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

/** Same rules as the backend's SchoolAdminSet. */
export function adminLoginErrors(f: AdminLoginForm) {
  return {
    full_name: f.full_name.trim().length < 2 ? "Enter the admin's name." : null,
    email: !EMAIL.test(f.email.trim()) ? "Enter a valid email address." : null,
    password:
      f.password.length < 8
        ? "At least 8 characters."
        : !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password)
          ? "Use at least one letter and one number."
          : null,
    confirm: f.confirm !== f.password ? "Passwords don't match." : null,
  };
}

export const adminLoginValid = (f: AdminLoginForm) => Object.values(adminLoginErrors(f)).every((e) => !e);

/** A readable random password: letters + digits, no look-alikes (0/O, 1/l). */
function generatePassword() {
  const letters = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ";
  const digits = "23456789";
  const pick = (s: string, n: number) => {
    const buf = new Uint32Array(n);
    crypto.getRandomValues(buf);
    return Array.from(buf, (x) => s[x % s.length]).join("");
  };
  return `${pick(letters, 4)}${pick(digits, 4)}${pick(letters, 2)}`;
}

/** Name, email and password (+ confirm) for a school admin login.
 *  Errors show once a field has been touched, or all at once with `showAll`. */
export function AdminLoginFields({
  idPrefix,
  value,
  onChange,
  showAll = false,
}: {
  idPrefix: string;
  value: AdminLoginForm;
  onChange: (v: AdminLoginForm) => void;
  showAll?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const [touched, setTouched] = useState<Partial<Record<keyof AdminLoginForm, boolean>>>({});
  const errors = adminLoginErrors(value);
  const shown = (k: keyof AdminLoginForm) => (showAll || touched[k] ? errors[k] : null);
  const set = (k: keyof AdminLoginForm, v: string) => onChange({ ...value, [k]: v });
  const touch = (k: keyof AdminLoginForm) => () => setTouched((t) => ({ ...t, [k]: true }));

  const field = (
    k: keyof AdminLoginForm,
    label: string,
    props: React.InputHTMLAttributes<HTMLInputElement> = {},
  ) => (
    <div className="space-y-1.5">
      <Label htmlFor={`${idPrefix}-${k}`}>
        {label}
        <span className="text-destructive"> *</span>
      </Label>
      <Input
        id={`${idPrefix}-${k}`}
        value={value[k]}
        onChange={(e) => set(k, e.target.value)}
        onBlur={touch(k)}
        className={cn(shown(k) && "border-destructive")}
        {...props}
      />
      {shown(k) && <p className="text-xs text-destructive">{shown(k)}</p>}
    </div>
  );

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {field("full_name", "Admin name", { placeholder: "e.g. Asha Rao", autoComplete: "off" })}
      {field("email", "Login email", { type: "email", placeholder: "admin@yourschool.edu", autoComplete: "off" })}

      <div className="space-y-1.5">
        <Label htmlFor={`${idPrefix}-password`}>
          Password<span className="text-destructive"> *</span>
        </Label>
        <div className="relative">
          <Input
            id={`${idPrefix}-password`}
            type={visible ? "text" : "password"}
            value={value.password}
            autoComplete="new-password"
            onChange={(e) => set("password", e.target.value)}
            onBlur={touch("password")}
            className={cn("pr-11 font-mono", shown("password") && "border-destructive")}
          />
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? "Hide password" : "Show password"}
            className="absolute inset-y-0 right-2 my-auto flex h-8 w-8 items-center justify-center rounded text-muted-foreground hover:bg-muted"
          >
            {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {shown("password") ? (
          <p className="text-xs text-destructive">{shown("password")}</p>
        ) : (
          <p className="text-xs text-muted-foreground">8+ characters with a letter and a number.</p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`${idPrefix}-confirm`}>
          Confirm password<span className="text-destructive"> *</span>
        </Label>
        <Input
          id={`${idPrefix}-confirm`}
          type={visible ? "text" : "password"}
          value={value.confirm}
          autoComplete="new-password"
          onChange={(e) => set("confirm", e.target.value)}
          onBlur={touch("confirm")}
          className={cn("font-mono", shown("confirm") && "border-destructive")}
        />
        {shown("confirm") && <p className="text-xs text-destructive">{shown("confirm")}</p>}
      </div>

      <div className="sm:col-span-2">
        <button
          type="button"
          onClick={() => {
            const p = generatePassword();
            onChange({ ...value, password: p, confirm: p });
            setVisible(true);
          }}
          className="inline-flex items-center gap-1.5 rounded-md border border-saffron-pale px-3 py-1.5 text-sm font-medium text-indigo-dark hover:bg-saffron-pale/60"
        >
          <Wand2 className="h-4 w-4" />
          Generate a password
        </button>
      </div>
    </div>
  );
}

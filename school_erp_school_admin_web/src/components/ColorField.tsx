import { Check, Pipette } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export const HEX = /^#[0-9a-fA-F]{6}$/;

/** Quick picks that read well as school brand colours. */
const PRESETS: { hex: string; name: string }[] = [
  { hex: "#E85D2E", name: "Saffron" },
  { hex: "#0F766E", name: "Teal" },
  { hex: "#3B2F7A", name: "Indigo" },
  { hex: "#1D4ED8", name: "Royal blue" },
  { hex: "#0284C7", name: "Sky blue" },
  { hex: "#15803D", name: "Green" },
  { hex: "#CA8A04", name: "Gold" },
  { hex: "#9F1239", name: "Maroon" },
  { hex: "#7E22CE", name: "Purple" },
  { hex: "#334155", name: "Slate" },
];

/** A colour with three ways to set it: the big swatch opens the browser's
 *  colour picker, the presets are one click, and the hex box takes a code. */
export function ColorField({
  id,
  label,
  value,
  onChange,
  error,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string | null;
}) {
  const valid = HEX.test(value);
  const current = value.toUpperCase();

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex items-center gap-3">
        <div
          className="relative h-11 w-16 shrink-0 overflow-hidden rounded-md border border-input shadow-sm"
          style={{ background: valid ? value : "repeating-conic-gradient(#e5e7eb 0 25%, #fff 0 50%) 0 0 / 12px 12px" }}
        >
          <input
            type="color"
            aria-label={`${label} picker`}
            title="Pick a colour"
            value={valid ? value.toLowerCase() : "#000000"}
            onChange={(e) => onChange(e.target.value.toUpperCase())}
            className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
          />
          <Pipette className="pointer-events-none absolute bottom-1 right-1 h-3.5 w-3.5 text-white drop-shadow" />
        </div>
        <Input
          id={id}
          value={value}
          maxLength={7}
          spellCheck={false}
          placeholder="#E85D2E"
          onChange={(e) => {
            const v = e.target.value.trim();
            onChange(v && !v.startsWith("#") ? `#${v}` : v);
          }}
          onBlur={() => valid && onChange(current)}
          className={cn("font-mono uppercase", error && "border-destructive")}
        />
      </div>
      <div className="flex flex-wrap gap-1.5" role="group" aria-label={`${label} presets`}>
        {PRESETS.map((p) => {
          const on = current === p.hex;
          return (
            <button
              key={p.hex}
              type="button"
              title={`${p.name} ${p.hex}`}
              aria-label={`${p.name} ${p.hex}`}
              aria-pressed={on}
              onClick={() => onChange(p.hex)}
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full border border-black/10 transition-transform hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                on && "ring-2 ring-indigo-dark ring-offset-2",
              )}
              style={{ background: p.hex }}
            >
              {on && <Check className="h-3.5 w-3.5 text-white" />}
            </button>
          );
        })}
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

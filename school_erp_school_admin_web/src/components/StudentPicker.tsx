import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { listStudents } from "@/features/students/api";

/** Typeahead picker for student_id fields.
 *
 *  Replaces every "type the student id by hand" input in the admin —
 *  hostel forms, fees collect, exam-marks entry. Server-side search
 *  via /v1/school-admin/students?q=... so it scales past first page.
 *
 *  Emits the selected student's numeric id as a string (so it slots
 *  into the existing `useState("")` patterns without refactoring). */
export function StudentPicker({
  value,
  onChange,
  placeholder = "Type student name or admission #",
}: {
  value: string;
  onChange: (id: string, label?: string) => void;
  placeholder?: string;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const list = useQuery({
    queryKey: ["picker-students", q],
    queryFn: () => listStudents({ q: q || undefined, limit: 12, offset: 0 }),
    enabled: q.length >= 1,
  });

  const items = useMemo(() => list.data?.items ?? [], [list.data]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Clear local label if parent cleared the value.
  useEffect(() => {
    if (!value) setSelectedLabel(null);
  }, [value]);

  return (
    <div ref={wrapperRef} className="relative">
      {value && selectedLabel ? (
        <div className="flex items-center justify-between rounded-md border border-input bg-saffron-pale/30 px-3 py-2 text-sm">
          <span className="truncate">
            <span className="font-medium text-indigo-dark">
              {selectedLabel}
            </span>
            <span className="ml-2 text-xs text-muted-foreground">
              (#{value})
            </span>
          </span>
          <button
            type="button"
            onClick={() => {
              onChange("");
              setSelectedLabel(null);
              setQ("");
              setOpen(true);
              setTimeout(() => inputRef.current?.focus(), 0);
            }}
            className="ml-2 text-muted-foreground hover:text-destructive"
            title="Change"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            ref={inputRef}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            placeholder={placeholder}
            className="pl-9"
          />
        </div>
      )}
      {open && !value && q.length >= 1 && (
        <div className="absolute z-30 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-input bg-background shadow-lg">
          {list.isLoading ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">
              Searching…
            </p>
          ) : items.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">
              No match.
            </p>
          ) : (
            items.map((s) => (
              <button
                key={s.id}
                type="button"
                className="block w-full px-3 py-2 text-left text-sm hover:bg-saffron-pale/40"
                onClick={() => {
                  onChange(String(s.id), s.full_name);
                  setSelectedLabel(s.full_name);
                  setOpen(false);
                  setQ("");
                }}
              >
                <div className="font-medium text-indigo-dark">
                  {s.full_name}
                </div>
                <div className="font-mono text-[10px] text-muted-foreground">
                  #{s.id} · {s.admission_number}
                  {s.current_class_label && ` · ${s.current_class_label}`}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * A dropdown you can type into to filter. With `allowCustom`, text that
 * isn't in the list is kept as the value (for places the list misses);
 * without it, the value must be one of `options`.
 */
export function Combobox({
  id,
  value,
  onChange,
  options,
  placeholder,
  allowCustom = false,
  invalid = false,
  emptyText = "No matches",
}: {
  id?: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder?: string;
  allowCustom?: boolean;
  invalid?: boolean;
  emptyText?: string;
}) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const listId = `${inputId}-list`;
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const [open, setOpen] = useState(false);
  // While typing, `query` holds the text; null means "show the value".
  const [query, setQuery] = useState<string | null>(null);
  const [active, setActive] = useState(0);

  const shown = useMemo(() => {
    const q = (query ?? "").trim().toLowerCase();
    if (!q) return options;
    const starts = options.filter((o) => o.toLowerCase().startsWith(q));
    const contains = options.filter((o) => !o.toLowerCase().startsWith(q) && o.toLowerCase().includes(q));
    return [...starts, ...contains];
  }, [options, query]);

  const typed = (query ?? "").trim();
  const exact = options.some((o) => o.toLowerCase() === typed.toLowerCase());
  const customRow = allowCustom && typed !== "" && !exact;
  const rows = customRow ? [...shown, `\u0000${typed}`] : shown;

  // Keep the highlighted row on screen while arrowing through a long list.
  useEffect(() => {
    if (!open) return;
    listRef.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  const choose = (v: string) => {
    onChange(v.startsWith("\u0000") ? v.slice(1) : v);
    setQuery(null);
    setOpen(false);
  };

  const openList = () => {
    setOpen(true);
    const i = options.indexOf(value);
    setActive(i >= 0 && query === null ? i : 0);
  };

  const close = () => {
    if (query !== null) {
      // Leaving the field: keep an exact match (any case) or custom text,
      // otherwise go back to the last real value.
      const match = options.find((o) => o.toLowerCase() === typed.toLowerCase());
      if (match) onChange(match);
      else if (allowCustom) onChange(typed);
    }
    setQuery(null);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) openList();
      else setActive((a) => Math.min(a + 1, rows.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      if (open && rows[active] !== undefined) {
        e.preventDefault();
        choose(rows[active]);
      }
    } else if (e.key === "Escape") {
      if (open) {
        // Only close the list, not a dialog the field sits in.
        e.preventDefault();
        e.stopPropagation();
        setQuery(null);
        setOpen(false);
      }
    }
  };

  return (
    <div className="relative">
      <input
        ref={inputRef}
        id={inputId}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && rows[active] !== undefined ? `${listId}-${active}` : undefined}
        autoComplete="off"
        value={query ?? value}
        placeholder={placeholder}
        onChange={(e) => {
          setQuery(e.target.value);
          setActive(0);
          setOpen(true);
          if (allowCustom) onChange(e.target.value);
        }}
        onFocus={openList}
        onClick={() => !open && openList()}
        onBlur={close}
        onKeyDown={onKeyDown}
        className={cn(
          "flex h-11 w-full rounded-md border border-input bg-background py-2 pl-4 pr-16 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          invalid && "border-destructive",
        )}
      />
      <div className="absolute inset-y-0 right-2 flex items-center gap-0.5">
        {value && (
          <button
            type="button"
            tabIndex={-1}
            aria-label="Clear"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              onChange("");
              setQuery(null);
              inputRef.current?.focus();
            }}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
        <button
          type="button"
          tabIndex={-1}
          aria-label="Show options"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => {
            if (open) setOpen(false);
            else {
              inputRef.current?.focus();
              openList();
            }
          }}
          className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
        </button>
      </div>

      {open && (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          className="absolute z-30 mt-1 max-h-64 w-full overflow-y-auto rounded-md border border-saffron-pale bg-warm-white py-1 text-sm shadow-lg"
        >
          {rows.length === 0 ? (
            <li className="px-4 py-2 text-muted-foreground">{emptyText}</li>
          ) : (
            rows.map((o, i) => {
              const custom = o.startsWith("\u0000");
              const label = custom ? o.slice(1) : o;
              const selected = !custom && o === value;
              return (
                <li
                  key={o}
                  id={`${listId}-${i}`}
                  data-index={i}
                  role="option"
                  aria-selected={selected}
                  onMouseDown={(e) => e.preventDefault()}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => choose(o)}
                  className={cn(
                    "flex cursor-pointer items-center justify-between gap-2 px-4 py-2",
                    i === active ? "bg-saffron-pale/70 text-indigo-dark" : "text-indigo-dark/90",
                    custom && "border-t border-saffron-pale italic",
                  )}
                >
                  <span className="truncate">{custom ? `Use “${label}”` : label}</span>
                  {selected && <Check className="h-4 w-4 shrink-0 text-saffron-dark" />}
                </li>
              );
            })
          )}
        </ul>
      )}
    </div>
  );
}

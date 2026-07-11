import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { listStudents } from "@/features/students/api";

/** Bulk ID-card generator. Reads students from the SIS, filters
 * by class + search, renders printable card previews. Print
 * dialog handles paper; CSS hides the sidebar during printing. */
export function IdCardsPage() {
  const [q, setQ] = useState("");
  const [classFilter, setClassFilter] = useState("");
  const [orgLine, setOrgLine] = useState("Demo Public School");

  const { data } = useQuery({
    queryKey: ["id-cards-students", q, classFilter],
    queryFn: () => listStudents({ q: q || undefined, limit: 200 }),
  });
  const students = data?.items ?? [];
  const filtered = useMemo(
    () =>
      classFilter
        ? students.filter((s) => (s.current_class_label ?? "").includes(classFilter))
        : students,
    [students, classFilter],
  );

  return (
    <div className="space-y-6 print:space-y-2">
      <header className="print:hidden">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-saffron-dark">
          Operations
        </p>
        <h1 className="mt-1 font-display text-4xl text-indigo-dark">ID cards</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
          Bulk-generate ID cards from your student roster. Filter by class,
          click Print — set page size to your card sheet in the browser dialog.
        </p>
      </header>

      <Card className="print:hidden">
        <CardHeader>
          <CardTitle>Filter + branding</CardTitle>
          <CardDescription>{filtered.length} cards will be rendered below</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label>Search</Label>
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name or admission" />
          </div>
          <div>
            <Label>Class filter</Label>
            <Input value={classFilter} onChange={(e) => setClassFilter(e.target.value)} placeholder="e.g. 8-A" />
          </div>
          <div className="col-span-2">
            <Label>School header (on every card)</Label>
            <Input value={orgLine} onChange={(e) => setOrgLine(e.target.value)} />
          </div>
          <div>
            <Button onClick={() => window.print()}>
              <Printer className="mr-1 h-4 w-4" /> Print all
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 print:grid-cols-3 print:gap-2">
        {filtered.map((s) => (
          <div
            key={s.id}
            className={cn(
              "flex flex-col overflow-hidden rounded-lg border-2 border-saffron bg-white shadow-sm",
              "print:break-inside-avoid print:shadow-none",
            )}
          >
            <div className="bg-saffron px-3 py-2 text-center text-warm-white">
              <p className="text-[10px] uppercase tracking-[0.2em]">{orgLine}</p>
              <p className="text-xs font-bold">STUDENT ID CARD</p>
            </div>
            <div className="flex flex-1 gap-3 p-3">
              <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded bg-muted text-4xl text-muted-foreground">
                {s.full_name.slice(0, 1)}
              </div>
              <div className="flex-1 text-xs">
                <p className="text-sm font-semibold text-indigo-dark">
                  {s.full_name}
                </p>
                <p className="mt-0.5 text-muted-foreground">
                  Admn: <span className="font-mono">{s.admission_number}</span>
                </p>
                <p className="text-muted-foreground">
                  Class: {s.current_class_label ?? "—"}
                </p>
                {s.roll_no && (
                  <p className="text-muted-foreground">Roll: {s.roll_no}</p>
                )}
                {s.blood_group && (
                  <p className="text-muted-foreground">Blood: {s.blood_group}</p>
                )}
              </div>
            </div>
            <div className="border-t border-input bg-muted/40 px-3 py-1 text-center text-[10px] text-muted-foreground">
              Valid for the academic session · If found, please return.
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="col-span-full text-sm text-muted-foreground">
            No students match. Adjust the filters above.
          </p>
        )}
      </div>
    </div>
  );
}

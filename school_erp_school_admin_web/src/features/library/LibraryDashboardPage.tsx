import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, ClipboardList, Hand, Layers, ReceiptText, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { reports } from "./api";
import { LibraryHeader, StatTile } from "./_shared";

/** Landing page for the librarian. Shows top-line counts (books,
 * copies, issued, overdue, outstanding fines) plus quick-jump cards
 * to every other Library sub-page. */
export function LibraryDashboardPage() {
  const { data } = useQuery({ queryKey: ["library-reports"], queryFn: reports });
  return (
    <div className="space-y-6">
      <LibraryHeader
        title="Library dashboard"
        subtitle="Circulation at a glance. Everything else — Books, Categories, Issue, Return, Fines, Reports — is in its own tab."
      />
      {data && (
        <div className="grid gap-4 md:grid-cols-5">
          <StatTile label="Books" value={data.total_books} />
          <StatTile label="Copies" value={data.total_copies} />
          <StatTile label="Issued" value={data.issued} tone="marigold" />
          <StatTile label="Overdue" value={data.overdue} tone="destructive" />
          <StatTile label="Fines due" value={`₹${data.fines_outstanding}`} tone="saffron" />
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        <QuickCard
          to="/library-books"
          icon={<BookOpen className="h-5 w-5" />}
          title="Books"
          desc="Add / edit titles, manage copies."
        />
        <QuickCard
          to="/library-categories"
          icon={<Layers className="h-5 w-5" />}
          title="Categories"
          desc="Genre / section breakdown."
        />
        <QuickCard
          to="/library-issue"
          icon={<Hand className="h-5 w-5" />}
          title="Issue books"
          desc="Loan a copy to a student or teacher."
        />
        <QuickCard
          to="/library-return"
          icon={<RotateCcw className="h-5 w-5" />}
          title="Return books"
          desc="Close out active loans, sweep overdue."
        />
        <QuickCard
          to="/library-fines"
          icon={<ReceiptText className="h-5 w-5" />}
          title="Fine management"
          desc="Collect or waive outstanding fines."
        />
        <QuickCard
          to="/library-reports"
          icon={<ClipboardList className="h-5 w-5" />}
          title="Reports"
          desc="Circulation & category-wise stats."
        />
      </div>
    </div>
  );
}

function QuickCard({
  to,
  icon,
  title,
  desc,
}: {
  to: string;
  icon: React.ReactNode;
  title: string;
  desc: string;
}) {
  return (
    <Link to={to} className="block">
      <Card className="h-full transition-colors hover:border-saffron">
        <CardHeader className="flex flex-row items-center gap-3 space-y-0">
          <div className="rounded-md bg-saffron-pale p-2 text-saffron-darker">{icon}</div>
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{desc}</p>
        </CardContent>
      </Card>
    </Link>
  );
}

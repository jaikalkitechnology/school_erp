import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LibraryHeader } from "./_shared";

/** Placeholder shell for Library sections whose backend isn't wired
 * yet. Renders the header, a short "coming soon" summary, and a
 * checklist of what the page will do — so the librarian knows the
 * section exists and what's planned without seeing a blank screen. */
export function LibraryStub({
  title,
  subtitle,
  planned,
}: {
  title: string;
  subtitle: string;
  planned: string[];
}) {
  return (
    <div className="space-y-6">
      <LibraryHeader title={title} subtitle={subtitle} />
      <Card>
        <CardHeader>
          <CardTitle>Coming soon</CardTitle>
          <CardDescription>
            This section is stubbed for the sidebar structure. The list
            below shows what it will do once wired to the backend.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            {planned.map((p) => (
              <li key={p} className="flex items-start gap-2">
                <span
                  aria-hidden
                  className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-saffron"
                />
                {p}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

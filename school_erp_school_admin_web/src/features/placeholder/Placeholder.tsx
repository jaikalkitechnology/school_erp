import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function Placeholder({ title, phase }: { title: string; phase: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>Implementation lands in {phase}.</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          This screen is part of the Jaikalki Super Admin scope. The Phase 0 foundation already
          provisioned the route, layout, and design tokens — feature code arrives next.
        </p>
      </CardContent>
    </Card>
  );
}

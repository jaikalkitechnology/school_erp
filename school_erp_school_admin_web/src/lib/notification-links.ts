import type { AppNotification } from "@/lib/notifications-api";

/**
 * Where a notification should open in the admin panel.
 *
 * The backend writes deeplinks for the mobile app ("/messages/12",
 * "/fees/invoices/9", ...). Most of those paths don't exist here, so map
 * each one to the admin page that shows the same thing. Returns null when
 * there's nowhere sensible to go (the click then just marks it read).
 */
export function adminPathFor(n: Pick<AppNotification, "deeplink" | "kind" | "source_type" | "source_id">): string | null {
  const link = n.deeplink ?? "";
  // Only ever follow in-app paths, never another site.
  const path = link.startsWith("/") && !link.startsWith("//") ? link : "";
  const parts = path.split("?")[0].split("/").filter(Boolean);
  const id = (i: number) => (parts[i] && /^\d+$/.test(parts[i]) ? parts[i] : null);

  switch (parts[0]) {
    case "messages":
      return id(1) ? `/communication?tab=Messages&message=${id(1)}` : "/communication?tab=Messages";
    case "announcements":
      return id(1) ? `/communication?tab=Announcements&announcement=${id(1)}` : "/communication";
    case "fees":
      return "/fees";
    case "homework":
      return "/homework";
    case "transport":
      return "/transport";
    case "students":
      return id(1) ? `/students/${id(1)}` : "/students";
    case "parent":
      // "/parent/dashboard/{studentId}" (eg. a leave decision).
      return parts[1] === "dashboard" && id(2) ? `/students/${id(2)}` : null;
    case "library":
      if (parts[1] === "loan") return "/library-issue";
      if (parts[1] === "reservation") return "/library-reservations";
      return "/library";
  }

  // No usable link: fall back on what the notification is about.
  if (n.source_type === "message") return n.source_id ? `/communication?tab=Messages&message=${n.source_id}` : "/communication?tab=Messages";
  if (n.source_type === "announcement") return n.source_id ? `/communication?tab=Announcements&announcement=${n.source_id}` : "/communication";
  return null;
}

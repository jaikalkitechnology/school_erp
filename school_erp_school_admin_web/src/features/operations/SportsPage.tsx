import { SimpleCrudPage, type FieldSpec } from "./_crud";
import {
  fetchSportsHouseOptions,
  fetchStudentOptions,
} from "./_pickers";

const HOUSE_FIELDS: FieldSpec[] = [
  { key: "name", label: "House", required: true },
  { key: "color", label: "Colour", placeholder: "#DC2626 or red" },
  { key: "motto", label: "Motto", hideInList: true },
  { key: "captain_student_id", label: "Captain", kind: "picker", fetchOptions: fetchStudentOptions },
  { key: "points", label: "Points", kind: "number" },
];

const EVENT_FIELDS: FieldSpec[] = [
  { key: "name", label: "Event", required: true },
  {
    key: "kind",
    label: "Kind",
    kind: "select",
    options: [
      { value: "tournament", label: "Tournament" },
      { value: "match", label: "Match" },
      { value: "practice", label: "Practice" },
      { value: "annual_day", label: "Annual day" },
      { value: "club", label: "Club" },
    ],
  },
  { key: "sport", label: "Sport", placeholder: "cricket / football / chess" },
  { key: "starts_on", label: "Starts", kind: "date", required: true },
  { key: "ends_on", label: "Ends", kind: "date" },
  { key: "venue", label: "Venue" },
  { key: "winner_house_id", label: "Winner house", kind: "picker", fetchOptions: fetchSportsHouseOptions, hideInList: true },
  { key: "notes", label: "Notes", kind: "textarea", hideInList: true },
];

export function SportsHousesPage() {
  return (
    <SimpleCrudPage
      title="Sports houses"
      subtitle="The four (or however many) houses your students belong to. Points accumulate across events — the leaderboard shows on the dashboard."
      endpoint="/v1/operations/sports-houses"
      queryKey="operations-sports-houses"
      fields={HOUSE_FIELDS}
    />
  );
}

export function SportsEventsPage() {
  return (
    <SimpleCrudPage
      title="Sports events"
      subtitle="Tournaments, inter-house matches, club sessions, annual day. Set a winning house when the event finishes to award points."
      endpoint="/v1/operations/sports-events"
      queryKey="operations-sports-events"
      fields={EVENT_FIELDS}
    />
  );
}

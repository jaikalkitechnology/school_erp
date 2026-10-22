import { useMemo } from "react";
import { Combobox } from "@/components/ui/combobox";
import { Label } from "@/components/ui/label";
import { INDIAN_STATES, citiesOf, findState } from "@/lib/india-locations";

/** State + City dropdowns. Picking a state narrows the city list to that
 *  state (and clears a city that isn't in it); a city the list doesn't
 *  have can be typed in. */
export function LocationFields({
  idPrefix,
  state,
  city,
  onState,
  onCity,
}: {
  idPrefix: string;
  state: string;
  city: string;
  onState: (v: string) => void;
  onCity: (v: string) => void;
}) {
  const cities = useMemo(() => citiesOf(state), [state]);
  const known = findState(state);

  return (
    <>
      <div className="space-y-1.5">
        <Label htmlFor={`${idPrefix}-state`}>State</Label>
        <Combobox
          id={`${idPrefix}-state`}
          value={state}
          options={INDIAN_STATES}
          placeholder="Select state"
          onChange={(v) => {
            onState(v);
            if (city && !citiesOf(v).some((c) => c.toLowerCase() === city.toLowerCase())) onCity("");
          }}
        />
        {state && !known && (
          <p className="text-xs text-marigold-dark">Not a state in the list. Pick one to fix the spelling.</p>
        )}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor={`${idPrefix}-city`}>City</Label>
        <Combobox
          id={`${idPrefix}-city`}
          value={city}
          onChange={onCity}
          options={cities}
          allowCustom
          placeholder={known ? `Select city in ${known}` : "Select city"}
          emptyText="Not in the list. Keep typing to use your own."
        />
      </div>
    </>
  );
}

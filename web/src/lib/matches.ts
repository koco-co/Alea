export interface MatchSummary {
  match_id: string;
  sporttery_match_number?: string | null;
  competition: string;
  home_team: string;
  away_team: string;
  kickoff_at: string;
  sales_cutoff_at?: string | null;
  state: string;
  sales_status?: string | null;
  fact_state: string;
  source_type?: string | null;
  source_authorization_status?: string | null;
  data_completeness: number;
  missing_fields: string[];
}

export interface MatchPage {
  matches: MatchSummary[];
  freshness_state: string;
}

export function beijingDate(value: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value);
  const read = (type: string) =>
    parts.find((part) => part.type === type)?.value;
  return `${read("year")}-${read("month")}-${read("day")}`;
}

export function addDays(date: string, offset: number): string {
  const [year, month, day] = date.split("-").map(Number);
  const value = new Date(Date.UTC(year, month - 1, day + offset));
  return value.toISOString().slice(0, 10);
}

export function dateLabel(date: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "numeric",
    day: "numeric",
  }).format(new Date(`${date}T00:00:00+08:00`));
}

export function kickoffLabel(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

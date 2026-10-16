export interface Raid {
  id: number;
  name: string;
  short_name: string;
}
export interface SavedRun {
  raid_id: number;
  raid_name: string;
  id: string;
  title: string;
  status: string;
  detail: string;
  when: string;
  updated: string;
  has_report: boolean;
  can_resume: boolean;
}
export interface Character {
  raid_id: number;
  raid_name: string;
  name: string;
  server: string;
  region: string;
  class_name: string;
  class_key: string;
  faction: string;
  ready: boolean;
  partition: number | null;
  partitions: { id: number; name: string }[];
  ambiguity: string | null;
  notes: string[];
  categories: { label: string; value: string }[];
  talent_trees: string[];
}
export interface EngineMessage {
  id?: number;
  result?: unknown;
  error?: string;
  event?: string;
  data?: unknown;
}
export interface RunResult {
  run?: SavedRun;
  stopped?: boolean;
  partial?: boolean;
}
export interface ReportResult {
  html: string;
  class_key: string;
  title: string;
}

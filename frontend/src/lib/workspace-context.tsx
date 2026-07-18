/**
 * Workspace context — React Context for `/projects/{id}` shared state.
 *
 * Per CLAUDE.md §5: Licht Zustand or React context — uses Context to avoid
 * adding a dependency that's not yet in package.json.
 *
 * One source of truth. Every workspace component (Topbar, PipelineStepper,
 * SceneSidebar, SceneFormPanel, ScenePlayer, ApproveBar) reads this.
 */

"use client";

import {
  createContext,
  useContext,
  useReducer,
  type ReactNode,
} from "react";

/* ── domain types ────────────────────────────────────── */

export type StepStatus = "locked" | "current" | "done" | "done-warning" | "error" | "stale";
export type SaveStatus = "saved" | "saving" | "error" | "offline";

/** Each step of the 5-station Pipeline. */
export const STATIONS: { key: string; label: string }[] = [
  { key: "research",  label: "Nghiên cứu" },
  { key: "content",   label: "Nội dung" },
  { key: "scenes",    label: "Phân cảnh" },
  { key: "finish",    label: "Hoàn thiện" },
  { key: "publish",   label: "Xuất bản" },
];

/**
 * Task 5-9: maps each Station (5-station pipeline UI) to the more granular
 * versioning `step` keys the backend tracks (app/models/step_version.py
 * `_STEP_ORDER`). Restore's `staled_steps` response uses the backend keys —
 * this is how a restore's stale cascade gets projected back onto the
 * station pills (BR-3/AC-2).
 */
export const STATION_VERSIONING_STEPS: readonly string[][] = [
  ["research"],
  ["outline", "script"],
  ["storyboard", "scene_set"],
  ["produce", "render"],
  ["publish"],
];

/** Index of the Station a given backend versioning-step key belongs to, or -1. */
export function stationIndexForVersioningStep(step: string): number {
  return STATION_VERSIONING_STEPS.findIndex((steps) => steps.includes(step));
}

export interface SceneRow {
  id: string;
  title: string;
  order: number;
  approved: boolean;
  warnings: string[];
  layoutClass: string;
}

/* ── state ───────────────────────────────────────────── */

export interface WorkspaceState {
  projectId: string;
  projectName: string;
  /** One of: idle | running | review | publish_ready | error */
  projectStatus: string;

  /* Pipeline */
  currentStation: number;
  stationStates: StepStatus[];

  /** 5-9: which backend versioning-step key the current station's
   * VersionSwitcher operates on (e.g. "scene_set" for the Scenes station).
   * Defaults from STATION_VERSIONING_STEPS; a station page may override via
   * SET_VERSIONING_STEP once it knows exactly which sub-step it edits. */
  versioningStep: string;

  /* Scenes */
  scenes: SceneRow[];
  selectedSceneIndex: number | null;
  approvedCount: number;

  /* Editor modes */
  readonly: boolean;
  unsavedChanges: boolean;
  saveStatus: SaveStatus;
  lastSaveError?: string;

  /* Drawer (5-10) */
  drawerOpen: boolean;
}

const makeState = (projectId: string): WorkspaceState => ({
  projectId,
  projectName: "",
  projectStatus: "idle",
  currentStation: 2,
  stationStates: ["done", "done", "current", "locked", "locked"],
  versioningStep: STATION_VERSIONING_STEPS[2][0],
  scenes: [],
  selectedSceneIndex: null,
  approvedCount: 0,
  readonly: false,
  unsavedChanges: false,
  saveStatus: "saved",
  drawerOpen: false,
});

/* ── reducer ─────────────────────────────────────────── */

type Action =
  | { type: "SET_PROJECT"; id: string; name?: string; status?: string }
  | { type: "SET_STATION_STATES"; states: StepStatus[] }
  | { type: "SET_CURRENT_STATION"; index: number }
  | { type: "SET_VERSIONING_STEP"; step: string }
  | { type: "MARK_STATIONS_STALE"; stationIndexes: number[] }
  | { type: "SET_SCENES"; scenes: SceneRow[] }
  | { type: "SELECT_SCENE"; index: number | null }
  | { type: "SET_READONLY"; v: boolean }
  | { type: "SET_SAVE_STATUS"; status: SaveStatus; error?: string }
  | { type: "SET_UNSAVED"; v: boolean }
  | { type: "OPEN_DRAWER" }
  | { type: "CLOSE_DRAWER" }
  | { type: "RESET" };

function reducer(state: WorkspaceState, action: Action): WorkspaceState {
  switch (action.type) {
    case "SET_PROJECT":
      return {
        ...state,
        projectId: action.id,
        ...(action.name !== undefined && { projectName: action.name }),
        ...(action.status !== undefined && { projectStatus: action.status }),
      };
    case "SET_STATION_STATES":
      return { ...state, stationStates: action.states };
    case "SET_CURRENT_STATION":
      return { ...state, currentStation: action.index };
    case "SET_VERSIONING_STEP":
      return { ...state, versioningStep: action.step };
    case "MARK_STATIONS_STALE": {
      const stationStates = [...state.stationStates];
      for (const idx of action.stationIndexes) {
        if (idx >= 0 && idx < stationStates.length) {
          stationStates[idx] = "stale";
        }
      }
      return { ...state, stationStates };
    }
    case "SET_SCENES":
      return {
        ...state,
        scenes: action.scenes,
        approvedCount: action.scenes.filter((s) => s.approved).length,
      };
    case "SELECT_SCENE":
      return { ...state, selectedSceneIndex: action.index };
    case "SET_READONLY":
      return { ...state, readonly: action.v };
    case "SET_SAVE_STATUS":
      return { ...state, saveStatus: action.status, lastSaveError: action.error };
    case "SET_UNSAVED":
      return { ...state, unsavedChanges: action.v };
    case "OPEN_DRAWER":
      return { ...state, drawerOpen: true };
    case "CLOSE_DRAWER":
      return { ...state, drawerOpen: false };
    case "RESET":
      return makeState(state.projectId);
    default:
      return state;
  }
}

/* ── Context ─────────────────────────────────────────── */

interface WorkspaceCtxValue {
  state: WorkspaceState;
  dispatch: React.Dispatch<Action>;
}

const WorkspaceCtx = createContext<WorkspaceCtxValue | null>(null);

export function WorkspaceProvider({
  children,
  projectId,
  initialState,
}: {
  children: ReactNode;
  projectId: string;
  initialState?: Partial<WorkspaceState>;
}) {
  const [state, dispatch] = useReducer(
    reducer,
    makeState(projectId),
    (init) => ({ ...init, ...initialState }),
  );

  return (
    <WorkspaceCtx.Provider value={{ state, dispatch }}>
      {children}
    </WorkspaceCtx.Provider>
  );
}

/** Hook: throw if called outside <WorkspaceProvider>. */
export function useWorkspace(): WorkspaceCtxValue {
  const ctx = useContext(WorkspaceCtx);
  if (!ctx) {
    throw new Error("useWorkspace must be wrapped in <WorkspaceProvider>");
  }
  return ctx;
}

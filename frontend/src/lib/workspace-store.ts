/**
 * Workspace store — Zustand singleton for `/projects/{id}` state.
 *
 * Scope (5-1): currentStation, projectId, scenes, selectedSceneId,
 *               stepperStates, approveCount, readonly mode, unsavedChanges,
 *               projectName, projectStatus.
 * Epics 5-2+ will extend this shape — never delete a field silently.
 */

import { create } from "zustand";
import { devtools, subscribeWithSelector } from "zustand/middleware";

/* ── Types ────────────────────────────────────────────── */

export type StepStatus = "locked" | "current" | "done" | "done-warning" | "error";

export interface Station {
  key: string;
  label: string;      // display text e.g. "Nghiên cứu"
}

export const STATIONS: Station[] = [
  { key: "research",  label: "Nghiên cứu" },
  { key: "content",   label: "Nội dung" },
  { key: "scenes",    label: "Phân cảnh" },
  { key: "finish",    label: "Hoàn thiện" },
  { key: "publish",   label: "Xuất bản" },
];

export interface Scene {
  id: string;
  title: string;
  status: string;
  approved: boolean;
  warnings?: string[];
  [key: string]: unknown;
}

/* ── Store ────────────────────────────────────────────── */

interface WorkspaceState {
  /* connection */
  projectId: string | null;
  projectName: string;
  projectStatus: "idle" | "running" | "review" | "publish_ready" | "error";

  /* stepper */
  currentStation: number;        // index into STATIONS (0-4)
  stationStates: StepStatus[];   // parallel to STATIONS

  /* scenes */
  scenes: Scene[];
  selectedSceneId: string | null;

  /* ui */
  readonly: boolean;
  unsavedChanges: boolean;
  saveStatus: "saved" | "saving" | "error" | "offline";

  /* drawer */
  drawerOpen: boolean;
}

interface WorkspaceActions {
  setProject: (id: string, name: string) => void;
  setProjectStatus: (status: WorkspaceState["projectStatus"]) => void;
  setCurrentStation: (index: number) => void;
  setStationState: (index: number, state: StepStatus) => void;
  setScenes: (scenes: Scene[]) => void;
  selectScene: (id: string | null) => void;
  setReadonly: (v: boolean) => void;
  setSaveStatus: (s: WorkspaceState["saveStatus"]) => void;
  setUnsavedChanges: (v: boolean) => void;
  openDrawer: () => void;
  closeDrawer: () => void;
  reset: () => void;
}

type WorkspaceStore = WorkspaceState & WorkspaceActions;

const INITIAL_STATE: WorkspaceState = {
  projectId: null,
  projectName: "",
  projectStatus: "idle",
  currentStation: 2,     // Scenes — where BR-1 BR-2 BR-3 live
  stationStates: ["done", "done", "current", "locked", "locked"],
  scenes: [],
  selectedSceneId: null,
  readonly: false,
  unsavedChanges: false,
  saveStatus: "saved",
  drawerOpen: false,
};

export const useWorkspaceStore = create<WorkspaceStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      ...INITIAL_STATE,

      setProject: (id: string, name: string) =>
        set({ projectId: id, projectName: name }),

      setProjectStatus: (projectStatus) => set({ projectStatus }),

      setCurrentStation: (currentStation) => set({ currentStation }),

      setStationState: (index: number, state: StepStatus) =>
        set((s) => {
          const next = [...s.stationStates];
          next[index] = state;
          return { stationStates: next };
        }),

      setScenes: (scenes) =>
        set({
          scenes,
          approvedCount: scenes.filter((sc) => sc.approved).length,
        }),

      selectScene: (selectedSceneId) => set({ selectedSceneId }),

      setReadonly: (readonly) => set({ readonly }),

      setSaveStatus: (saveStatus) => set({ saveStatus }),

      setUnsavedChanges: (unsavedChanges) => set({ unsavedChanges }),

      openDrawer: () => set({ drawerOpen: true }),
      closeDrawer: () => set({ drawerOpen: false }),

      reset: () => set(INITIAL_STATE),
    })),
    { name: "workspace" },
  ),
);

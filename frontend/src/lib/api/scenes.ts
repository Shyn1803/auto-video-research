/**
 * Scenes API client — GET/PUT wiring for task 5-2 (5-1 left this as a
 * placeholder: "5-2 wires the real PUT /api/scenes/{id}").
 *
 * Matches `backend/app/api/scenes.py` (api-spec.md §6): `GET
 * /projects/{id}/scenes` returns the full Scene JSON list + `approved`;
 * `PUT /projects/{id}/scenes/{scene_id}` autosaves one scene and 422s with
 * `{field_path, message}` on an invalid payload.
 */

import { api } from "./interceptor";
import type { SceneJson } from "@/lib/scene/types";

export interface SceneListItem extends SceneJson {
  approved: boolean;
}

export async function listScenes(projectId: string): Promise<SceneListItem[]> {
  const { data } = await api.get(`/projects/${projectId}/scenes`);
  return Array.isArray(data) ? data : (data.scenes ?? []);
}

export async function getScene(projectId: string, sceneId: string): Promise<SceneListItem> {
  const scenes = await listScenes(projectId);
  const found = scenes.find((s) => s.scene_id === sceneId);
  if (!found) {
    throw new Error(`scene ${sceneId} not found in project ${projectId}`);
  }
  return found;
}

export interface ScenePutError {
  field_path: string[];
  message: string;
}

export async function putScene(
  projectId: string,
  sceneId: string,
  payload: SceneJson,
): Promise<SceneJson> {
  const { data } = await api.put(`/projects/${projectId}/scenes/${sceneId}`, payload);
  return data;
}

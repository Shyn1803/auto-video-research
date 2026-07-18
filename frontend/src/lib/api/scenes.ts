/**
 * Scene ops API client (Task 5-4) — thin wrappers over the §6 endpoints.
 *
 * Every call here is optimistic-UI-then-confirm: the caller (SceneSidebar,
 * AddSceneButton, DeleteSceneDialog, DuplicateSceneButton) updates local
 * workspace-context state via sceneOpsReducer immediately, then fires the
 * matching request. On failure the caller is responsible for reverting
 * (re-fetching list_scenes) — this module does not own retry/rollback.
 */

import { api } from "@/lib/api/interceptor";

export async function reorderScenesApi(
  projectId: string,
  sceneIds: string[],
): Promise<void> {
  await api.post(`/projects/${projectId}/scenes/reorder`, { scene_ids: sceneIds });
}

export async function addSceneApi(
  projectId: string,
  afterSceneNumber: number,
  layout: string,
): Promise<{ scene_id: string }> {
  const res = await api.post(`/projects/${projectId}/scenes`, {
    after_scene_number: afterSceneNumber,
    layout,
  });
  return res.data;
}

export async function deleteSceneApi(projectId: string, sceneId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/scenes/${sceneId}`);
}

export async function duplicateSceneApi(
  projectId: string,
  sceneId: string,
): Promise<{ scene_id: string }> {
  const res = await api.post(`/projects/${projectId}/scenes/${sceneId}/duplicate`);
  return res.data;
}

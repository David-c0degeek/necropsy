import { invoke, isTauri } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { EngineMessage } from "./types";

type Receiver = (event: EngineMessage) => void;
let nextId = 0;
const waiting = new Map<
  number,
  { resolve: (value: unknown) => void; reject: (error: Error) => void }
>();
let receiver: Receiver = () => {};

export const native = isTauri();

export async function startEngine(
  onEvent: Receiver,
  onExit: () => void,
): Promise<() => void> {
  receiver = onEvent;
  if (!native) {
    throw new Error(
      "Open Necropsy as a desktop app to use your saved analyses. For development, run npm run desktop.",
    );
  }
  const stop = await listen<EngineMessage>("engine-message", ({ payload }) => {
    if (payload.event) receiver(payload);
    if (payload.id !== undefined) {
      const pending = waiting.get(payload.id);
      if (pending) {
        waiting.delete(payload.id);
        if (payload.error) pending.reject(new Error(payload.error));
        else pending.resolve(payload.result);
      }
    }
  });
  const exit = await listen("engine-exit", () => {
    for (const pending of waiting.values())
      pending.reject(
        new Error(
          "The analysis engine stopped. Restart Necropsy to continue your saved work.",
        ),
      );
    waiting.clear();
    onExit();
  });
  try {
    await invoke("start_engine");
  } catch (error) {
    stop();
    exit();
    throw error;
  }
  return () => {
    stop();
    exit();
  };
}

export function request<T>(
  method: string,
  params: Record<string, unknown> = {},
): Promise<T> {
  const id = ++nextId;
  return new Promise<T>((resolve, reject) => {
    waiting.set(id, { resolve: (value) => resolve(value as T), reject });
    invoke("engine_request", { message: { id, method, params } }).catch(
      (error) => {
        waiting.delete(id);
        reject(new Error(String(error)));
      },
    );
  });
}

export async function chooseFolder(): Promise<string | null> {
  const { open } = await import("@tauri-apps/plugin-dialog");
  return await open({
    directory: true,
    multiple: false,
    title: "Choose a saved Necropsy analysis folder",
  });
}

export async function chooseSnapshot(): Promise<string | null> {
  const { open } = await import("@tauri-apps/plugin-dialog");
  return await open({
    multiple: false,
    title: "Open a Necropsy snapshot",
    filters: [{ name: "Snapshot", extensions: ["zip"] }],
  });
}

export async function chooseExport(): Promise<string | null> {
  const { save } = await import("@tauri-apps/plugin-dialog");
  return await save({
    defaultPath: "necropsy-analysis.zip",
    title: "Export analysis package",
    filters: [{ name: "ZIP package", extensions: ["zip"] }],
  });
}

export async function quit(): Promise<void> {
  await invoke("quit_app");
}
export async function onClose(callback: () => void): Promise<() => void> {
  return await listen("desktop-close", callback);
}

import type { ApiConfig } from "./types";

export function apiDisplayName(config: Pick<ApiConfig, "id" | "display_name">) {
  return config.display_name?.trim() || config.id;
}

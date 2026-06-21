import { useEffect, type ReactNode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../api/client";
import type { ApiConfig } from "../api/types";
import { AppStateProvider, useAppState } from "../state/AppState";
import { ApiConfigPage } from "./ApiConfigPage";

function SeedWarnings({ children }: { children: ReactNode }) {
  const { dispatch } = useAppState();
  useEffect(() => {
    dispatch({
      type: "set_local_config_warnings",
      warnings: [
        {
          domain: "api_config",
          message: "API 配置文件损坏，已恢复为默认配置",
          path: "api_configs.json",
          backup_path: "api_configs.json.bak",
          backup_failed: false
        },
        {
          domain: "user_settings",
          message: "用户设置文件损坏，已恢复为默认设置",
          path: "user_settings.json",
          backup_path: "user_settings.json.bak",
          backup_failed: false
        }
      ]
    });
  }, [dispatch]);

  return <>{children}</>;
}

const seededApiConfig: ApiConfig = {
  id: "api1",
  display_name: "主力 API",
  url: "https://api.example.test/v1",
  key: "secret",
  model: "old-model",
  max_tokens: 4096,
  temperature: 0.7,
  stream: true,
  timeout: 180,
  max_retries: 3,
  is_active: true,
  key_env_var: "",
  has_key: true,
  has_env_key: false
};

function SeedApiConfigs({ children }: { children: ReactNode }) {
  const { dispatch } = useAppState();
  useEffect(() => {
    dispatch({ type: "set_api_configs", items: [seededApiConfig] });
  }, [dispatch]);

  return <>{children}</>;
}

describe("ApiConfigPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows local configuration recovery warnings in their settings surface", async () => {
    render(
      <AppStateProvider>
        <SeedWarnings>
          <ApiConfigPage />
        </SeedWarnings>
      </AppStateProvider>
    );

    expect(await screen.findByText(/API 配置文件损坏/)).toBeInTheDocument();
    expect(screen.getByText(/用户设置文件损坏/)).toBeInTheDocument();
  });

  it("describes max_retries as API total attempts", async () => {
    render(
      <AppStateProvider>
        <ApiConfigPage />
      </AppStateProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: /新增/ }));

    expect(screen.getByText("API 总尝试次数")).toBeInTheDocument();
    expect(screen.getByText("包含第一次请求；例如 3 表示最多发起 3 次请求。")).toBeInTheDocument();
  });

  it("fetches model options for the model combobox while keeping manual input", async () => {
    const fetchModels = vi
      .spyOn(apiClient, "fetchModels")
      .mockResolvedValue(["model-a", "model-b"]);

    render(
      <AppStateProvider>
        <SeedApiConfigs>
          <ApiConfigPage />
        </SeedApiConfigs>
      </AppStateProvider>
    );

    const modelInput = await screen.findByLabelText("模型");
    expect(modelInput).toHaveValue("old-model");

    fireEvent.change(modelInput, { target: { value: "manual-model" } });
    expect(modelInput).toHaveValue("manual-model");

    fireEvent.click(screen.getByRole("button", { name: "获取模型列表" }));

    await waitFor(() => {
      expect(fetchModels).toHaveBeenCalledWith(
        expect.objectContaining({ id: "api1", model: "manual-model" })
      );
    });

    const listId = modelInput.getAttribute("list");
    expect(listId).toBeTruthy();

    await waitFor(() => {
      const modelList = document.getElementById(listId ?? "");
      const options = Array.from(modelList?.querySelectorAll("option") ?? []).map(
        (option) => option.value
      );
      expect(options).toEqual(["model-a", "model-b"]);
    });

    fireEvent.change(modelInput, { target: { value: "model-b" } });
    expect(modelInput).toHaveValue("model-b");
    expect(screen.getByText("已获取 2 个模型，可下拉选择或继续手输模型 ID。")).toBeInTheDocument();
  });
});

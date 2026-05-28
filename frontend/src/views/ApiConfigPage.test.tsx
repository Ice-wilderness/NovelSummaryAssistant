import { useEffect, type ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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

describe("ApiConfigPage", () => {
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
});

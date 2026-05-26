import { describe, expect, it } from "vitest";

describe("frontend test setup", () => {
  it("runs vitest in the Vite workspace", () => {
    expect("trigger-scan").toContain("scan");
  });
});

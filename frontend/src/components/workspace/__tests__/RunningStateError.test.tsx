/**
 * RunningStateError tests — Task 5-8 Step 3 (BR-2).
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import RunningStateError from "../RunningStateError";

describe("RunningStateError — AllProvidersFailed", () => {
  const error = {
    kind: "all_providers_failed" as const,
    capability: "llm_cheap",
    chain: ["ollama", "groq"],
    failures: [
      { provider: "ollama", reason: "unreachable", retryable: true },
      { provider: "groq", reason: "quota exceeded", retryable: false },
    ],
  };

  it("admin view: shows provider+reason list and a Quản trị › Providers link", () => {
    render(<RunningStateError error={error} viewerRole="admin" />);
    expect(screen.getByText(/ollama/)).toBeInTheDocument();
    expect(screen.getByText(/unreachable/)).toBeInTheDocument();
    expect(screen.getByText(/quota exceeded/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Quản trị › Providers/ })).toHaveAttribute(
      "href",
      "/admin/api-keys",
    );
  });

  it("creator view: shows the provider list but not the admin link, tells them to report it", () => {
    render(<RunningStateError error={error} viewerRole="creator" />);
    expect(screen.getByText(/ollama/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Quản trị/ })).toBeNull();
    expect(screen.getByText(/báo quản trị viên/)).toBeInTheDocument();
  });
});

describe("RunningStateError — generic error", () => {
  it("shows a translated message with technical detail collapsed by default", () => {
    render(
      <RunningStateError
        error={{
          kind: "generic",
          message: "Đã xảy ra lỗi khi tạo phân cảnh.",
          technicalDetail: "TypeError: cannot read property 'x' of undefined",
        }}
        viewerRole="creator"
      />,
    );
    expect(screen.getByText("Đã xảy ra lỗi khi tạo phân cảnh.")).toBeInTheDocument();
    const details = screen.getByText("Chi tiết kỹ thuật").closest("details");
    expect(details).not.toHaveAttribute("open");
    expect(screen.getByText(/TypeError/)).toBeInTheDocument();
  });

  it("calls onRetry when Thử lại is clicked", () => {
    const onRetry = vi.fn();
    render(
      <RunningStateError
        error={{ kind: "generic", message: "Lỗi chung." }}
        viewerRole="creator"
        onRetry={onRetry}
      />,
    );
    screen.getByText("Thử lại").click();
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

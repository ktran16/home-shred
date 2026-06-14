import { render, screen } from "@testing-library/react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RestTimer } from "@/components/rest-timer";

describe("RestTimer", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  const tick = () =>
    act(() => {
      vi.advanceTimersByTime(1000);
    });

  it("counts down each second and reaches 'Go!' at zero", () => {
    render(<RestTimer seconds={3} onDismiss={() => {}} />);
    expect(screen.getByText("3s")).toBeInTheDocument();

    tick();
    expect(screen.getByText("2s")).toBeInTheDocument();
    tick();
    expect(screen.getByText("1s")).toBeInTheDocument();
    tick();
    expect(screen.getByText("Go!")).toBeInTheDocument();
  });
});

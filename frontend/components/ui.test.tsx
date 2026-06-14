import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Badge, Button } from "@/components/ui";

describe("ui primitives", () => {
  it("Button renders children and fires onClick", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save profile</Button>);
    const btn = screen.getByRole("button", { name: "Save profile" });
    fireEvent.click(btn);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("Badge renders its label", () => {
    render(<Badge>compound</Badge>);
    expect(screen.getByText("compound")).toBeInTheDocument();
  });
});

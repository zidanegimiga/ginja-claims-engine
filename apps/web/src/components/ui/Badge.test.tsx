import { render, screen } from "@testing-library/react";
import { DecisionBadge } from "./Badge";

describe("DecisionBadge", () => {
  it("renders Pass correctly", () => {
    render(<DecisionBadge decision="Pass" />);
    expect(screen.getByText("Pass")).toBeInTheDocument();
  });

  it("renders Flag correctly", () => {
    render(<DecisionBadge decision="Flag" />);
    expect(screen.getByText("Flag")).toBeInTheDocument();
  });

  it("renders Fail correctly", () => {
    render(<DecisionBadge decision="Fail" />);
    expect(screen.getByText("Fail")).toBeInTheDocument();
  });

  it("applies correct class for Pass", () => {
    const { container } = render(<DecisionBadge decision="Pass" />);
    expect(container.firstChild).toHaveClass("text-emerald-400");
  });

  it("applies correct class for Fail", () => {
    const { container } = render(<DecisionBadge decision="Fail" />);
    expect(container.firstChild).toHaveClass("text-red-400");
  });
});
/* eslint-disable @typescript-eslint/no-explicit-any */
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatPercent,
  formatDuration,
  truncateId,
  getDecisionColor,
  getRiskColor,
} from "./utils";

describe("formatCurrency", () => {
  it("formats KES correctly", () => {
    const result = formatCurrency(12500, "KES");
    expect(result).toContain("12,500");
  });

  it("returns em dash for null", () => {
    expect(formatCurrency(null as any)).toBe("—");
  });

  it("returns em dash for undefined", () => {
    expect(formatCurrency(undefined as any)).toBe("—");
  });

  it("returns em dash for NaN", () => {
    expect(formatCurrency(NaN)).toBe("—");
  });

  it("handles zero", () => {
    const result = formatCurrency(0);
    expect(result).toContain("0");
  });
});

describe("formatDate", () => {
  it("returns em dash for null", () => {
    expect(formatDate(null as any)).toBe("—");
  });

  it("returns em dash for invalid date", () => {
    expect(formatDate("not-a-date")).toBe("—");
  });

  it("formats a valid date", () => {
    const result = formatDate("2026-03-13T00:00:00Z");
    expect(result).toContain("2026");
  });
});

describe("formatDateTime", () => {
  it("returns em dash for undefined", () => {
    expect(formatDateTime(undefined as any)).toBe("—");
  });

  it("formats a valid datetime", () => {
    const result = formatDateTime("2026-03-13T14:30:00Z");
    expect(result).toContain("2026");
  });
});

describe("formatPercent", () => {
  it("formats 0.75 as 75.0%", () => {
    expect(formatPercent(0.75)).toBe("75.0%");
  });

  it("respects decimal places", () => {
    expect(formatPercent(0.1234, 2)).toBe("12.34%");
  });
});

describe("formatDuration", () => {
  it("shows ms for under 1 second", () => {
    expect(formatDuration(250)).toBe("250ms");
  });

  it("shows seconds for over 1000ms", () => {
    expect(formatDuration(1500)).toBe("1.5s");
  });
});

describe("truncateId", () => {
  it("truncates long ids", () => {
    expect(truncateId("abcdefghijklmnop", 8)).toBe("abcdefgh…");
  });

  it("leaves short ids unchanged", () => {
    expect(truncateId("abc", 8)).toBe("abc");
  });
});

describe("getDecisionColor", () => {
  it("returns green for Pass", () => {
    expect(getDecisionColor("Pass")).toContain("success");
  });

  it("returns red for Fail", () => {
    expect(getDecisionColor("Fail")).toContain("destructive");
  });
});

describe("getRiskColor", () => {
  it("returns green for low risk", () => {
    expect(getRiskColor(0.1)).toContain("success");
  });

  it("returns red for high risk", () => {
    expect(getRiskColor(0.9)).toContain("destructive");
  });
});
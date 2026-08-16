import { describe, expect, it } from "vitest";

import { formatApiErrorDetail } from "./api";

describe("formatApiErrorDetail", () => {
  it("returns FastAPI string details", () => {
    expect(formatApiErrorDetail("Unsupported CV type")).toBe("Unsupported CV type");
  });

  it("formats structured FastAPI validation details", () => {
    expect(
      formatApiErrorDetail([
        {
          loc: ["body", "source_options", "Greenhouse", "boards"],
          msg: "Input should be a valid list",
          type: "list_type",
        },
      ]),
    ).toBe("source_options → Greenhouse → boards: Input should be a valid list");
  });
});

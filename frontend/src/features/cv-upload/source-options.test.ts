import { describe, expect, it } from "vitest";

import { SourceDescriptor } from "@/lib/api";
import { serializeSelectedSourceOptions } from "./source-options";

const descriptors: SourceDescriptor[] = [
  {
    source_id: "Greenhouse",
    display_name: "Greenhouse",
    capabilities: {
      configuration_fields: [
        {
          key: "boards",
          label: "Board names",
          kind: "string_list",
          required: true,
          help_text: null,
        },
      ],
    },
  },
  {
    source_id: "ApprovedSource",
    display_name: "Approved source",
    capabilities: {
      configuration_fields: [
        {
          key: "api_key",
          label: "API key",
          kind: "secret",
          required: true,
          help_text: null,
        },
      ],
    },
  },
  {
    source_id: "Lever",
    display_name: "Lever",
    capabilities: {
      configuration_fields: [
        {
          key: "companies",
          label: "Company names",
          kind: "string_list",
          required: true,
          help_text: null,
        },
      ],
    },
  },
  {
    source_id: "Ashby",
    display_name: "Ashby",
    capabilities: {
      configuration_fields: [
        {
          key: "organizations",
          label: "Organization names",
          kind: "string_list",
          required: true,
          help_text: null,
        },
      ],
    },
  },
];

describe("serializeSelectedSourceOptions", () => {
  it("serializes one string-list value as an array", () => {
    expect(
      serializeSelectedSourceOptions(["Greenhouse"], descriptors, {
        Greenhouse: { boards: "openai" },
      }),
    ).toEqual({ Greenhouse: { boards: ["openai"] } });
  });

  it.each([
    ["Lever", "companies", "netflix"],
    ["Ashby", "organizations", "linear"],
  ])("serializes one %s target as an array", (sourceId, key, value) => {
    expect(
      serializeSelectedSourceOptions([sourceId], descriptors, {
        [sourceId]: { [key]: value },
      }),
    ).toEqual({ [sourceId]: { [key]: [value] } });
  });

  it("submits options and secrets only for selected sources", () => {
    expect(
      serializeSelectedSourceOptions(["Greenhouse"], descriptors, {
        Greenhouse: { boards: "openai, stripe" },
        ApprovedSource: { api_key: "synthetic-secret-value" },
      }),
    ).toEqual({ Greenhouse: { boards: ["openai", "stripe"] } });
  });

  it("reports a missing required value before submission", () => {
    expect(() =>
      serializeSelectedSourceOptions(["Greenhouse"], descriptors, {}),
    ).toThrow("Greenhouse: Board names is required.");
  });
});

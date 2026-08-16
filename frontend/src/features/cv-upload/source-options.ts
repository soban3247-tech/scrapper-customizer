import { SourceDescriptor } from "@/lib/api";

export type SourceOptionInputs = Record<string, Record<string, string>>;
export type SerializedSourceOptions = Record<string, Record<string, unknown>>;

export function serializeSelectedSourceOptions(
  selectedSourceIds: string[],
  descriptors: SourceDescriptor[],
  inputs: SourceOptionInputs,
): SerializedSourceOptions {
  const descriptorsById = new Map(
    descriptors.map((descriptor) => [descriptor.source_id, descriptor]),
  );

  return Object.fromEntries(
    selectedSourceIds.flatMap((sourceId) => {
      const descriptor = descriptorsById.get(sourceId);
      if (!descriptor) return [];

      const values = Object.fromEntries(
        descriptor.capabilities.configuration_fields.flatMap((field) => {
          const rawValue = inputs[sourceId]?.[field.key]?.trim() ?? "";
          if (!rawValue) {
            if (field.required) {
              throw new Error(`${descriptor.display_name}: ${field.label} is required.`);
            }
            return [];
          }

          const serializedValue = serializeFieldValue(field.kind, rawValue);
          if (
            field.required &&
            Array.isArray(serializedValue) &&
            serializedValue.length === 0
          ) {
            throw new Error(`${descriptor.display_name}: ${field.label} is required.`);
          }
          return [[field.key, serializedValue]];
        }),
      );

      return Object.keys(values).length > 0 ? [[sourceId, values]] : [];
    }),
  );
}

function serializeFieldValue(
  kind: SourceDescriptor["capabilities"]["configuration_fields"][number]["kind"],
  value: string,
): unknown {
  if (kind === "string_list") {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (kind === "integer") {
    const parsed = Number(value);
    if (!Number.isInteger(parsed)) throw new Error("Enter a whole number.");
    return parsed;
  }
  if (kind === "boolean") {
    if (value.toLowerCase() === "true") return true;
    if (value.toLowerCase() === "false") return false;
    throw new Error('Enter "true" or "false".');
  }
  return value;
}

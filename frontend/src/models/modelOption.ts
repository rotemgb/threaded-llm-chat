export type ModelOption = {
  key: string;
  label: string;
  provider?: string;
  isDefault?: boolean;
};

export function toModelOptions(modelKeys: string[]): ModelOption[] {
  return modelKeys.map((key, idx) => ({
    key,
    label: key.replaceAll("_", " "),
    isDefault: idx === 0,
  }));
}

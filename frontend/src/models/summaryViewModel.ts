export type Summary = {
  id: number;
  level: number;
  summary_text: string;
  created_at: string;
};

export function selectLatestSummaryText(summaries: Summary[]): string | null {
  if (!summaries.length) {
    return null;
  }
  const global = summaries
    .filter((s) => s.level === 2)
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )[0];
  return global?.summary_text ?? summaries[summaries.length - 1].summary_text;
}

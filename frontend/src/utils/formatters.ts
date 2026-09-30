export function formatNumber(val: number | null | undefined): string {
  if (val === null || val === undefined) return 'N/A';
  return val.toLocaleString();
}

export function formatPercent(val: number | null | undefined): string {
  if (val === null || val === undefined) return 'N/A';
  const prefix = val > 0 ? '+' : '';
  return `${prefix}${val.toFixed(2)}%`;
}

export function formatDate(isoStr: string | null | undefined): string {
  if (!isoStr) return 'N/A';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

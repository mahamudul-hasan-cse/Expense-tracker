export const EXPENSES_PAGE_SIZE = 20;

export interface ExpenseFilterState {
  page: number;
  /** "" or "all" means no category filter (the Select's "All Categories" value) */
  categoryFilter: string;
  startDate: string;
  endDate: string;
  search: string;
}

/** Turn the list page's filter state into API query params, dropping empty filters. */
export function buildExpenseQuery({ page, categoryFilter, startDate, endDate, search }: ExpenseFilterState) {
  const trimmed = search.trim();
  return {
    page,
    limit: EXPENSES_PAGE_SIZE,
    category_id: categoryFilter && categoryFilter !== "all" ? categoryFilter : undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    search: trimmed || undefined,
  };
}

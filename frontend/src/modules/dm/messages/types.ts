export type DMQueryState = {
  fetchedAt: number | null;
  isLoadingInitial: boolean;
  isLoadingOlder: boolean;
  isLoadingNewer: boolean;
  hasMoreOlder: boolean;
  hasMoreNewer: boolean;
  nextBefore: string | null;
  nextAfter: string | null;
  error: string | null;
};

export const defaultDMQueryState: DMQueryState = {
  fetchedAt: null,
  isLoadingInitial: false,
  isLoadingOlder: false,
  isLoadingNewer: false,
  hasMoreOlder: true,
  hasMoreNewer: false,
  nextBefore: null,
  nextAfter: null,
  error: null,
};

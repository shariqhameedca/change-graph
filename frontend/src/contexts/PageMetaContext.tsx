import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface PageMetaContextValue {
  crumbLabel: string | null;
  setCrumbLabel: (label: string | null) => void;
}

const PageMetaContext = createContext<PageMetaContextValue | null>(null);

export function PageMetaProvider({ children }: { children: ReactNode }) {
  const [crumbLabel, setCrumbLabel] = useState<string | null>(null);
  return (
    <PageMetaContext.Provider value={{ crumbLabel, setCrumbLabel }}>{children}</PageMetaContext.Provider>
  );
}

/** Lets a page override the last breadcrumb segment with a real name once
 * its data has loaded (e.g. the regulation's name instead of its id). */
export function usePageCrumb(label: string | null | undefined) {
  const ctx = useContext(PageMetaContext);
  useEffect(() => {
    ctx?.setCrumbLabel(label ?? null);
    return () => ctx?.setCrumbLabel(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [label]);
}

export function usePageMetaContext() {
  return useContext(PageMetaContext);
}

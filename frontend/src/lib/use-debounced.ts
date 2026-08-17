"use client";

import { useEffect, useState } from "react";

/**
 * Trails `value` by `delay` ms.
 *
 * Filter inputs feed straight into `useAsync` dependency lists, so without this
 * every keystroke in a search box is one request to the API.
 */
export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

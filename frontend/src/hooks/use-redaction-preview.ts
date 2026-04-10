import { useDeferredValue, useEffect, useState } from "react";

import { previewRedaction } from "@/lib/api";
import type { RedactionPreview } from "@/types";

export function useRedactionPreview(text: string, enabled = true) {
  const deferredText = useDeferredValue(text);
  const [preview, setPreview] = useState<RedactionPreview | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPreview() {
      if (!enabled || !deferredText.trim()) {
        setPreview(null);
        return;
      }

      try {
        const result = await previewRedaction(deferredText);
        if (!cancelled) {
          setPreview(result);
        }
      } catch {
        if (!cancelled) {
          setPreview(null);
        }
      }
    }

    void loadPreview();
    return () => {
      cancelled = true;
    };
  }, [deferredText, enabled]);

  return preview;
}

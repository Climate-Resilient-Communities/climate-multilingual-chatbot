
"use client";

import { useEffect, useState } from "react";

const MOBILE_BREAKPOINT = 768; // Corresponds to md: breakpoint in Tailwind

export function useIsMobile() {
  const [isMobile, setIsMobile] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    const checkDevice = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    };

    // Check on mount
    checkDevice();

    // Add listener for window resize
    window.addEventListener("resize", checkDevice);

    // Cleanup listener on unmount
    return () => {
      window.removeEventListener("resize", checkDevice);
    };
  }, []);

  return isMobile;
}

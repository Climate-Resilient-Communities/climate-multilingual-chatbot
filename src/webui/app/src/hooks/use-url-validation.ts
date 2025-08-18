/**
 * Hook for managing URL validation and broken link notifications
 */

import { useState, useEffect, useCallback } from 'react';
import { useToast } from '@/hooks/use-toast';
import { 
  validateSources, 
  type ValidatedSource,
  type UrlValidationResult 
} from '@/lib/url-validation';

export interface UseUrlValidationOptions {
  autoValidate?: boolean;
  showNotifications?: boolean;
  validateOnMount?: boolean;
  silentMode?: boolean; // Don't show notifications, just validate
}

export interface UseUrlValidationReturn {
  validatedSources: ValidatedSource[];
  isValidating: boolean;
  hasValidationErrors: boolean;
  brokenLinks: ValidatedSource[];
  validateSources: (sources: ValidatedSource[]) => Promise<void>;
  retryValidation: () => Promise<void>;
  clearValidation: () => void;
}

export function useUrlValidation(
  initialSources: ValidatedSource[] = [],
  options: UseUrlValidationOptions = {}
): UseUrlValidationReturn {
  const {
    autoValidate = true,
    showNotifications = false, // Default to false to reduce noise
    validateOnMount = true,
    silentMode = false
  } = options;

  const [validatedSources, setValidatedSources] = useState<ValidatedSource[]>(initialSources);
  const [isValidating, setIsValidating] = useState(false);
  const [originalSources, setOriginalSources] = useState<ValidatedSource[]>(initialSources);
  const { toast } = useToast();

  const validateSourcesCallback = useCallback(async (sources: ValidatedSource[]) => {
    if (!sources.length) {
      setValidatedSources([]);
      return;
    }

    setIsValidating(true);
    setOriginalSources(sources);

    try {
      const validated = await validateSources(sources);
      setValidatedSources(validated);

      // Show notifications for broken links if enabled and not in silent mode
      if (showNotifications && !silentMode) {
        // Only consider actual HTTP/HTTPS URLs that were validated and failed
        const actualBrokenLinks = validated.filter(source => 
          !source.isValid && 
          source.validationError && 
          (source.url.startsWith('http://') || source.url.startsWith('https://'))
        );
        
        if (actualBrokenLinks.length > 0) {
          // Show a single notification for broken links with PDF fallbacks
          const linksWithPdf = actualBrokenLinks.filter(link => link.fallbackPdf);
          const linksWithoutPdf = actualBrokenLinks.filter(link => !link.fallbackPdf);

          if (linksWithPdf.length > 0) {
            toast({
              title: "Broken Links Found",
              description: `${linksWithPdf.length} link(s) appear to be broken. PDF alternatives are available.`,
              variant: "default",
            });
          }

          if (linksWithoutPdf.length > 0) {
            toast({
              title: "Unavailable Links",
              description: `${linksWithoutPdf.length} link(s) are currently unavailable.`,
              variant: "destructive",
            });
          }
        }
      }
    } catch (error) {
      console.error('URL validation failed:', error);
      if (showNotifications) {
        toast({
          title: "Validation Error",
          description: "Unable to validate links at this time. Please try again later.",
          variant: "destructive",
        });
      }
      // Fallback to original sources
      setValidatedSources(sources);
    } finally {
      setIsValidating(false);
    }
  }, [showNotifications, toast]);

  const retryValidation = useCallback(async () => {
    if (originalSources.length > 0) {
      await validateSourcesCallback(originalSources);
    }
  }, [originalSources, validateSourcesCallback]);

  const clearValidation = useCallback(() => {
    setValidatedSources([]);
    setOriginalSources([]);
    setIsValidating(false);
  }, []);

  // Auto-validate on mount and when sources change
  useEffect(() => {
    if (validateOnMount && autoValidate && initialSources.length > 0) {
      validateSourcesCallback(initialSources);
    }
  }, [initialSources, autoValidate, validateOnMount, validateSourcesCallback]);

  // Computed values
  const hasValidationErrors = validatedSources.some(source => !source.isValid);
  const brokenLinks = validatedSources.filter(source => !source.isValid);

  return {
    validatedSources,
    isValidating,
    hasValidationErrors,
    brokenLinks,
    validateSources: validateSourcesCallback,
    retryValidation,
    clearValidation
  };
}
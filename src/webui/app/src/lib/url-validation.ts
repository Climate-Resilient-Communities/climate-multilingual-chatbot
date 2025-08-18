/**
 * URL Validation Service for Climate Multilingual Chatbot
 * Handles URL liveness checks and PDF fallback functionality
 */

export interface UrlValidationResult {
  isValid: boolean;
  statusCode?: number;
  error?: string;
  responseTime?: number;
  contentType?: string;
}

export interface ValidatedSource {
  url: string;
  title: string;
  text: string;
  content?: string;
  snippet?: string;
  isValid?: boolean;
  fallbackPdf?: string;
  validationError?: string;
}

/**
 * Cache for URL validation results to avoid redundant checks
 */
class UrlValidationCache {
  private cache = new Map<string, { result: UrlValidationResult; timestamp: number }>();
  private readonly cacheExpiryMs = 5 * 60 * 1000; // 5 minutes

  get(url: string): UrlValidationResult | null {
    const cached = this.cache.get(url);
    if (!cached) return null;
    
    const isExpired = Date.now() - cached.timestamp > this.cacheExpiryMs;
    if (isExpired) {
      this.cache.delete(url);
      return null;
    }
    
    return cached.result;
  }

  set(url: string, result: UrlValidationResult): void {
    this.cache.set(url, { result, timestamp: Date.now() });
  }

  clear(): void {
    this.cache.clear();
  }

  getStats(): { size: number; urls: string[] } {
    return {
      size: this.cache.size,
      urls: Array.from(this.cache.keys())
    };
  }
}

const validationCache = new UrlValidationCache();

/**
 * Validates if a URL is accessible and returns status information
 */
export async function validateUrl(url: string, timeoutMs: number = 5000): Promise<UrlValidationResult> {
  // Check cache first
  const cached = validationCache.get(url);
  if (cached) {
    return cached;
  }

  const startTime = Date.now();
  
  try {
    // Validate URL format first
    try {
      new URL(url);
    } catch {
      const result: UrlValidationResult = {
        isValid: false,
        error: 'Invalid URL format'
      };
      validationCache.set(url, result);
      return result;
    }

    // Create an AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      // Use HEAD request first for efficiency, then fallback to GET if needed
      let response = await fetch(url, {
        method: 'HEAD',
        signal: controller.signal,
        headers: {
          'User-Agent': 'Climate-Chatbot-LinkValidator/1.0'
        }
      });

      // If HEAD fails with 405 (Method Not Allowed), try GET
      if (!response.ok && response.status === 405) {
        response = await fetch(url, {
          method: 'GET',
          signal: controller.signal,
          headers: {
            'User-Agent': 'Climate-Chatbot-LinkValidator/1.0'
          }
        });
      }

      clearTimeout(timeoutId);
      
      const responseTime = Date.now() - startTime;
      const contentType = response.headers.get('content-type') || undefined;

      const result: UrlValidationResult = {
        isValid: response.ok,
        statusCode: response.status,
        responseTime,
        contentType,
        error: response.ok ? undefined : `HTTP ${response.status}: ${response.statusText}`
      };

      validationCache.set(url, result);
      return result;

    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      let errorMessage = 'Network error';
      if (fetchError instanceof Error) {
        if (fetchError.name === 'AbortError') {
          errorMessage = 'Request timeout';
        } else {
          errorMessage = fetchError.message;
        }
      }

      const result: UrlValidationResult = {
        isValid: false,
        error: errorMessage,
        responseTime: Date.now() - startTime
      };

      validationCache.set(url, result);
      return result;
    }

  } catch (error) {
    const result: UrlValidationResult = {
      isValid: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      responseTime: Date.now() - startTime
    };

    validationCache.set(url, result);
    return result;
  }
}

/**
 * Generates PDF fallback URL for a given source
 * This function can be customized based on your PDF storage strategy
 */
export function generatePdfFallback(url: string, title: string): string | null {
  try {
    const urlObj = new URL(url);
    const domain = urlObj.hostname;
    
    // Strategy 1: Check if it's a common government/academic domain with known PDF patterns
    const knownPdfDomains = [
      'canada.ca',
      'gc.ca',
      'toronto.ca',
      'ontario.ca',
      'ipcc.ch',
      'unfccc.int',
      'nature.com',
      'sciencedirect.com'
    ];

    const isKnownDomain = knownPdfDomains.some(knownDomain => 
      domain.includes(knownDomain) || domain.endsWith(knownDomain)
    );

    if (isKnownDomain) {
      // Try to construct PDF URL by replacing html extensions or adding .pdf
      let pdfUrl = url;
      
      // Replace common HTML extensions with .pdf
      if (url.includes('.html') || url.includes('.htm')) {
        pdfUrl = url.replace(/\.(html?)(.*)?$/i, '.pdf');
      }
      // If URL ends with a path without extension, try adding .pdf
      else if (!url.includes('.') && !url.endsWith('/')) {
        pdfUrl = url + '.pdf';
      }
      // For URLs ending with /, try adding a PDF filename based on title
      else if (url.endsWith('/')) {
        const filename = title.toLowerCase()
          .replace(/[^a-z0-9\s]/gi, '')
          .replace(/\s+/g, '-')
          .substring(0, 50);
        pdfUrl = url + filename + '.pdf';
      }
      
      return pdfUrl !== url ? pdfUrl : null;
    }

    // Strategy 2: For academic papers, try common PDF URL patterns
    if (domain.includes('doi.org') || domain.includes('arxiv.org') || domain.includes('researchgate.net')) {
      // These platforms often have PDF download links
      if (domain.includes('arxiv.org') && url.includes('/abs/')) {
        return url.replace('/abs/', '/pdf/') + '.pdf';
      }
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Check if a source URL should be validated (only HTTP/HTTPS URLs)
 */
function shouldValidateUrl(url: string): boolean {
  return url.startsWith('http://') || url.startsWith('https://');
}

/**
 * Validates a list of sources and provides fallback options for broken links
 */
export async function validateSources(sources: ValidatedSource[]): Promise<ValidatedSource[]> {
  const validatedSources = await Promise.all(
    sources.map(async (source) => {
      // Only validate actual HTTP/HTTPS URLs
      if (!shouldValidateUrl(source.url)) {
        // For non-URLs (DOI, references, etc.), just pass through without validation
        return {
          ...source,
          isValid: true, // Consider non-URLs as "valid" since they're not web links
          fallbackPdf: undefined,
          validationError: undefined
        };
      }

      const validation = await validateUrl(source.url);
      
      let fallbackPdf: string | undefined;
      let validationError: string | undefined;

      if (!validation.isValid) {
        // Try to generate PDF fallback
        fallbackPdf = generatePdfFallback(source.url, source.title) || undefined;
        validationError = validation.error;
        
        // If we have a fallback PDF, validate it too
        if (fallbackPdf) {
          const pdfValidation = await validateUrl(fallbackPdf);
          if (!pdfValidation.isValid) {
            fallbackPdf = undefined; // Remove fallback if it's also invalid
          }
        }
      }

      return {
        ...source,
        isValid: validation.isValid,
        fallbackPdf,
        validationError
      };
    })
  );

  return validatedSources;
}

/**
 * Check if URL points to a PDF document
 */
export function isPdfUrl(url: string): boolean {
  try {
    const urlObj = new URL(url);
    return urlObj.pathname.toLowerCase().endsWith('.pdf');
  } catch {
    return false;
  }
}

/**
 * Clear the validation cache (useful for testing or manual refresh)
 */
export function clearValidationCache(): void {
  validationCache.clear();
}

/**
 * Get cache statistics (useful for debugging)
 */
export function getCacheStats(): { size: number; urls: string[] } {
  return validationCache.getStats();
}
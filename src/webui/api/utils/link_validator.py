"""
Server-side URL validation for inline links in LLM responses
Validates and sanitizes markdown links to prevent broken links reaching users
"""

import asyncio
import aiohttp
import re
import logging
from typing import Dict, Tuple, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Markdown link pattern: [text](url)
MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

# Cache for URL validation results (in-memory for session)
_url_validation_cache: Dict[str, Tuple[bool, str]] = {}

async def validate_url_server_side(url: str, timeout: int = 5) -> Tuple[bool, str]:
    """
    Validate URL server-side using aiohttp to avoid CORS issues.
    Returns (is_valid, fallback_url) where fallback_url is the root domain if original fails.
    """
    # Check cache first
    cache_key = url
    if cache_key in _url_validation_cache:
        cached_result = _url_validation_cache[cache_key]
        if isinstance(cached_result, tuple):
            return cached_result
        else:
            # Old cache format, convert
            return (cached_result, url if cached_result else "")
    
    try:
        # Parse URL to ensure it's valid
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            result = (False, "")
            _url_validation_cache[cache_key] = result
            return result
        
        # Only validate HTTP/HTTPS URLs
        if parsed.scheme not in ['http', 'https']:
            result = (True, url)  # Assume non-HTTP URLs are valid (mailto, etc.)
            _url_validation_cache[cache_key] = result
            return result
        
        # Perform HEAD request to check if URL is accessible
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            try:
                async with session.head(url, allow_redirects=True) as response:
                    is_valid = response.status < 400
                    if is_valid:
                        result = (True, url)
                        _url_validation_cache[cache_key] = result
                        return result
            except Exception:
                pass
            
            # If HEAD fails, try GET with minimal data
            try:
                async with session.get(url, allow_redirects=True) as response:
                    is_valid = response.status < 400
                    if is_valid:
                        result = (True, url)
                        _url_validation_cache[cache_key] = result
                        return result
            except Exception:
                pass
            
            # Original URL failed, try root domain fallback
            root_url = f"{parsed.scheme}://{parsed.netloc}"
            if root_url != url:  # Don't test the same URL twice
                try:
                    async with session.head(root_url, allow_redirects=True) as response:
                        if response.status < 400:
                            result = (False, root_url)  # Original failed, but root works
                            _url_validation_cache[cache_key] = result
                            return result
                except Exception:
                    pass
            
            # Both original and root failed
            result = (False, "")
            _url_validation_cache[cache_key] = result
            return result
                    
    except Exception as e:
        logger.debug(f"URL validation failed for {url}: {str(e)}")
        result = (False, "")
        _url_validation_cache[cache_key] = result
        return result

def extract_markdown_links(text: str) -> List[Tuple[str, str, str]]:
    """
    Extract markdown links from text.
    Returns list of tuples: (full_match, link_text, url)
    """
    matches = []
    for match in MARKDOWN_LINK_PATTERN.finditer(text):
        full_match = match.group(0)  # [text](url)
        link_text = match.group(1)   # text
        url = match.group(2)         # url
        matches.append((full_match, link_text, url))
    return matches

def is_google_drive_link(url: str) -> bool:
    """Check if URL is a Google Drive link that should be treated as PDF."""
    return 'drive.google.com' in url.lower() or 'docs.google.com' in url.lower()

async def validate_and_fix_inline_links(response_text: str) -> Tuple[str, Dict]:
    """
    Validate inline markdown links in LLM response and replace broken ones.
    Respects existing Google Drive -> PDF Document logic.
    
    Args:
        response_text: The LLM response containing potential markdown links
        
    Returns:
        Tuple of (sanitized_text, validation_report)
    """
    if not response_text:
        return response_text, {"total_links": 0, "validated": 0, "broken": 0, "fixed": 0, "google_drive": 0}
    
    links = extract_markdown_links(response_text)
    if not links:
        return response_text, {"total_links": 0, "validated": 0, "broken": 0, "fixed": 0, "google_drive": 0}
    
    logger.info(f"Validating {len(links)} inline links in LLM response")
    
    # Process links and handle Google Drive specially
    sanitized_text = response_text
    validation_stats = {"total_links": len(links), "validated": 0, "broken": 0, "fixed": 0, "google_drive": 0}
    
    # Separate Google Drive links from regular links
    google_drive_links = []
    regular_links = []
    
    for i, (full_match, link_text, url) in enumerate(links):
        if is_google_drive_link(url):
            google_drive_links.append((i, full_match, link_text, url))
        else:
            regular_links.append((i, full_match, link_text, url))
    
    # Handle Google Drive links - convert to PDF document references
    for i, full_match, link_text, url in google_drive_links:
        replacement = f"{link_text} (PDF Document)"
        sanitized_text = sanitized_text.replace(full_match, replacement, 1)
        validation_stats["google_drive"] += 1
        validation_stats["fixed"] += 1
        logger.info(f"Converted Google Drive link to PDF reference: {link_text}")
    
    # Validate regular links concurrently
    if regular_links:
        validation_tasks = []
        for _, _, _, url in regular_links:
            validation_tasks.append(validate_url_server_side(url))
        
        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # Process regular link validation results
        for j, (i, full_match, link_text, url) in enumerate(regular_links):
            try:
                result = validation_results[j]
                if isinstance(result, tuple) and len(result) == 2:
                    is_valid, fallback_url = result
                    validation_stats["validated"] += 1
                    
                    if not is_valid:
                        validation_stats["broken"] += 1
                        
                        if fallback_url:
                            # Replace with fallback URL (root domain)
                            replacement = f"[{link_text}]({fallback_url})"
                            sanitized_text = sanitized_text.replace(full_match, replacement, 1)
                            validation_stats["fixed"] += 1
                            logger.info(f"Replaced broken link with root domain: {url} -> {fallback_url}")
                        else:
                            # No fallback available, use plain text
                            replacement = f"{link_text} (link currently unavailable)"
                            sanitized_text = sanitized_text.replace(full_match, replacement, 1)
                            validation_stats["fixed"] += 1
                            logger.warning(f"Replaced broken inline link with no fallback: {url}")
                elif isinstance(result, bool):
                    # Legacy format handling
                    validation_stats["validated"] += 1
                    if not result:
                        validation_stats["broken"] += 1
                        replacement = f"{link_text} (link currently unavailable)"
                        sanitized_text = sanitized_text.replace(full_match, replacement, 1)
                        validation_stats["fixed"] += 1
                        
            except Exception as e:
                logger.error(f"Error processing link validation result: {str(e)}")
                validation_stats["broken"] += 1
                
                # Replace problematic link with plain text
                replacement = f"{link_text} (link unavailable)"
                sanitized_text = sanitized_text.replace(full_match, replacement, 1)
                validation_stats["fixed"] += 1
    
    if validation_stats["fixed"] > 0:
        logger.info(f"Fixed {validation_stats['fixed']} inline links: {validation_stats['google_drive']} Google Drive, {validation_stats['broken']} broken")
    
    return sanitized_text, validation_stats

def clear_url_cache():
    """Clear the URL validation cache."""
    global _url_validation_cache
    _url_validation_cache.clear()
    logger.info("URL validation cache cleared")
"""
Web Scraper Module for Article Summarizer Agent
Enhanced with Advanced WAF Bypassing Techniques + Selenium Integration
"""

import requests
import time
import logging
import re
import hashlib
import chardet
import random
import json
import base64
from urllib.parse import urlparse, urljoin, parse_qs
from typing import Dict, Optional, Tuple, List
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ssl
import socket
from urllib3.util.ssl_ import create_urllib3_context

from config import config, CONTENT_SELECTORS, UNWANTED_SELECTORS

# Try to import Selenium integration
try:
    from .selenium_scraper import AdvancedSeleniumScraper
    SELENIUM_INTEGRATION_AVAILABLE = True
except ImportError:
    SELENIUM_INTEGRATION_AVAILABLE = False

class WebScraper:
    """Advanced web scraper with comprehensive WAF bypassing techniques"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = self._create_advanced_session()
        self.cache = {}
        self.proxy_list = self._load_proxy_list()
        self.current_proxy_index = 0
        self.browser_profiles = self._create_browser_profiles()
        self.current_profile_index = 0
        
        # Initialize Selenium integration for advanced WAF bypassing
        self.selenium_scraper = None
        if SELENIUM_INTEGRATION_AVAILABLE:
            try:
                self.selenium_scraper = AdvancedSeleniumScraper()
                self.logger.info("🚀 Selenium integration enabled - Advanced WAF bypassing available")
            except Exception as e:
                self.logger.warning(f"Selenium integration failed: {e}")
        else:
            self.logger.info("📦 Selenium not available - Install selenium, webdriver-manager, and undetected-chromedriver for advanced WAF bypassing")
        
    def _create_browser_profiles(self) -> List[Dict]:
        """Create comprehensive browser profiles for advanced fingerprinting evasion"""
        return [
            {
                'name': 'Chrome_Windows_Latest',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'sec_ch_ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Windows"',
                'sec_ch_ua_platform_version': '"15.0.0"',
                'viewport': '1920x1080',
                'screen': '1920x1080x24',
                'timezone': 'America/New_York',
                'language': 'en-US,en;q=0.9',
                'webgl_vendor': 'Google Inc. (NVIDIA)'
            },
            {
                'name': 'Chrome_MacOS_Latest',
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'sec_ch_ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"macOS"',
                'sec_ch_ua_platform_version': '"14.2.1"',
                'viewport': '1440x900',
                'screen': '1440x900x24',
                'timezone': 'America/Los_Angeles',
                'language': 'en-US,en;q=0.9',
                'webgl_vendor': 'Apple Inc.'
            },
            {
                'name': 'Firefox_Windows_Latest',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
                'sec_ch_ua': None,  # Firefox doesn't send these headers
                'sec_ch_ua_mobile': None,
                'sec_ch_ua_platform': None,
                'sec_ch_ua_platform_version': None,
                'viewport': '1920x1080',
                'screen': '1920x1080x24',
                'timezone': 'Europe/London',
                'language': 'en-US,en;q=0.5',
                'webgl_vendor': 'Mozilla'
            },
            {
                'name': 'Safari_MacOS_Latest',
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
                'sec_ch_ua': None,  # Safari doesn't send these headers
                'sec_ch_ua_mobile': None,
                'sec_ch_ua_platform': None,
                'sec_ch_ua_platform_version': None,
                'viewport': '1440x900',
                'screen': '1440x900x24',
                'timezone': 'America/Los_Angeles',
                'language': 'en-US,en;q=0.9',
                'webgl_vendor': 'Apple Inc.'
            },
            {
                'name': 'Edge_Windows_Latest',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
                'sec_ch_ua': '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Windows"',
                'sec_ch_ua_platform_version': '"15.0.0"',
                'viewport': '1920x1080',
                'screen': '1920x1080x24',
                'timezone': 'America/New_York',
                'language': 'en-US,en;q=0.9',
                'webgl_vendor': 'Google Inc. (NVIDIA)'
            }
        ]
    
    def _load_proxy_list(self) -> List[Dict]:
        """Load proxy list - in production, this would come from a proxy service"""
        # For now, return empty list - can be extended with proxy services
        return []
    
    def _create_advanced_session(self) -> requests.Session:
        """Create a session with advanced anti-detection features"""
        session = requests.Session()
        
        # Configure HTTP/2 support and advanced SSL context
        context = create_urllib3_context()
        context.set_ciphers('ECDHE+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH')
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Configure retry strategy with jitter
        retry_strategy = Retry(
            total=config.scraping.max_retries + 2,  # More retries for WAF
            status_forcelist=[403, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=config.scraping.backoff_factor,
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_current_browser_profile(self) -> Dict:
        """Get current browser profile and rotate"""
        profile = self.browser_profiles[self.current_profile_index]
        self.current_profile_index = (self.current_profile_index + 1) % len(self.browser_profiles)
        return profile
    
    def _set_advanced_headers(self, url: str, profile: Dict):
        """Set advanced headers based on browser profile"""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Base headers
        headers = {
            'User-Agent': profile['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': profile['language'],
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'same-site']),
            'Sec-Fetch-User': '?1',
        }
        
        # Add Chrome/Edge specific headers
        if profile['sec_ch_ua']:
            headers.update({
                'Sec-Ch-Ua': profile['sec_ch_ua'],
                'Sec-Ch-Ua-Mobile': profile['sec_ch_ua_mobile'],
                'Sec-Ch-Ua-Platform': profile['sec_ch_ua_platform'],
                'Sec-Ch-Ua-Platform-Version': profile['sec_ch_ua_platform_version'],
                'Sec-Ch-Ua-Full-Version-List': f'"{profile["name"].split("_")[0]}";v="121.0.6167.160", "Not A(Brand";v="99.0.0.0", "Chromium";v="121.0.6167.160"'
            })
        
        # Add viewport and screen information as custom headers (some sites check for these)
        headers['X-Viewport'] = profile['viewport']
        headers['X-Screen'] = profile['screen']
        
        # Randomize some headers
        if random.choice([True, False]):
            headers['Referer'] = random.choice([
                base_url,
                f"{base_url}/",
                "https://www.google.com/",
                "https://www.bing.com/"
            ])
        
        # Add timing headers to simulate real browser behavior
        headers['X-Requested-With'] = 'XMLHttpRequest' if random.random() < 0.1 else None
        
        # Remove None values
        headers = {k: v for k, v in headers.items() if v is not None}
        
        self.session.headers.update(headers)
    
    def _simulate_browser_behavior(self, url: str):
        """Simulate realistic browser behavior patterns"""
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Simulate preflight requests that browsers make
        preflight_urls = [
            f"{base_url}/favicon.ico",
            f"{base_url}/robots.txt",
            f"{base_url}/sitemap.xml"
        ]
        
        for preflight_url in preflight_urls:
            if random.random() < 0.3:  # 30% chance to make preflight request
                try:
                    # Quick HEAD request to simulate browser behavior
                    self.session.head(preflight_url, timeout=5, allow_redirects=False)
                    time.sleep(random.uniform(0.1, 0.5))
                except:
                    pass  # Ignore preflight failures
    
    def _add_browser_noise(self):
        """Add realistic browser noise and timing"""
        # Simulate JavaScript execution time
        js_execution_time = random.uniform(0.05, 0.2)
        time.sleep(js_execution_time)
        
        # Add random mouse movements simulation (via custom headers)
        self.session.headers.update({
            'X-Mouse-Position': f"{random.randint(0, 1920)},{random.randint(0, 1080)}",
            'X-Scroll-Position': f"{random.randint(0, 1000)}"
        })
    
    def _handle_cloudflare_challenge(self, response: requests.Response, url: str) -> Optional[requests.Response]:
        """Handle Cloudflare challenge pages"""
        if "Checking your browser" in response.text or "Just a moment" in response.text:
            self.logger.info("Detected Cloudflare challenge, attempting to solve...")
            
            # Extract challenge parameters
            challenge_match = re.search(r'challenge_id=([^&"]+)', response.text)
            if challenge_match:
                challenge_id = challenge_match.group(1)
                
                # Wait for "browser check" simulation
                wait_time = random.uniform(5, 8)
                self.logger.info(f"Simulating browser check wait: {wait_time:.1f}s")
                time.sleep(wait_time)
                
                # Try to get the page again after "challenge"
                try:
                    # Update headers to simulate successful challenge
                    self.session.headers.update({
                        'Referer': url,
                        'X-Cloudflare-Challenge': challenge_id
                    })
                    
                    new_response = self.session.get(url, timeout=config.scraping.timeout)
                    if new_response.status_code == 200:
                        return new_response
                except Exception as e:
                    self.logger.warning(f"Cloudflare challenge handling failed: {e}")
        
        return None
    
    def _handle_captcha_detection(self, response: requests.Response) -> bool:
        """Detect if page contains CAPTCHA"""
        captcha_indicators = [
            'captcha', 'recaptcha', 'hcaptcha', 'turnstile',
            'verify you are human', 'prove you are not a robot',
            'security check', 'bot detection'
        ]
        
        response_text = response.text.lower()
        return any(indicator in response_text for indicator in captcha_indicators)
    
    def scrape_article(self, url: str) -> Dict:
        """
        Advanced scraping method with comprehensive WAF bypassing
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        self.logger.info(f"Starting advanced scraping for URL: {url}")
        
        # Validate URL
        if not self._is_valid_url(url):
            raise ValueError(f"Invalid URL format: {url}")
        
        # Check cache first
        url_hash = self._get_url_hash(url)
        if config.output.cache_enabled and url_hash in self.cache:
            self.logger.info("Returning cached content")
            return self.cache[url_hash]
        
        # Get browser profile
        profile = self._get_current_browser_profile()
        self.logger.info(f"Using browser profile: {profile['name']}")
        
        try:
            # Set advanced headers
            self._set_advanced_headers(url, profile)
            
            # Simulate browser behavior
            self._simulate_browser_behavior(url)
            
            # Add browser noise
            self._add_browser_noise()
            
            # Fetch the page with advanced techniques
            response = self._fetch_page_advanced(url, profile)
            
            # Handle special cases
            if response.status_code == 403:
                # Try different approach for 403
                response = self._handle_403_advanced(url, profile)
            
            # Check for Cloudflare challenge
            if "cloudflare" in response.text.lower():
                cf_response = self._handle_cloudflare_challenge(response, url)
                if cf_response:
                    response = cf_response
            
            # Check for CAPTCHA
            if self._handle_captcha_detection(response):
                self.logger.warning("CAPTCHA detected - manual intervention may be required")
                # Could integrate CAPTCHA solving service here
            
            # Detect encoding
            encoding = self._detect_encoding(response)
            response.encoding = encoding
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content using multiple strategies
            content_data = self._extract_content(soup, url)
            
            # Add metadata
            content_data.update({
                'url': url,
                'status_code': response.status_code,
                'encoding': encoding,
                'scraped_at': time.time(),
                'content_length': len(response.text),
                'browser_profile': profile['name'],
                'bypass_techniques_used': [
                    'advanced_headers',
                    'browser_fingerprinting',
                    'behavioral_simulation',
                    'timing_randomization'
                ]
            })
            
            # Cache the result
            if config.output.cache_enabled:
                self.cache[url_hash] = content_data
            
            self.logger.info(f"Successfully scraped article: {content_data.get('title', 'Unknown')}")
            return content_data
            
        except Exception as e:
            self.logger.error(f"Regular scraping failed for {url}: {str(e)}")
            
            # Try Selenium as fallback for advanced WAF bypassing
            if self.selenium_scraper:
                self.logger.info("🔄 Attempting Selenium fallback for advanced WAF bypassing...")
                try:
                    selenium_result = self.selenium_scraper.scrape_with_selenium(url)
                    
                    # Cache the result if successful
                    if config.output.cache_enabled:
                        self.cache[url_hash] = selenium_result
                    
                    self.logger.info(f"✅ Selenium fallback successful: {selenium_result.get('title', 'Unknown')}")
                    return selenium_result
                    
                except Exception as selenium_error:
                    self.logger.error(f"❌ Selenium fallback also failed: {selenium_error}")
                    raise Exception(f"Both regular scraping and Selenium fallback failed. Regular: {str(e)}, Selenium: {str(selenium_error)}")
            else:
                self.logger.error("No Selenium fallback available - install selenium dependencies for advanced WAF bypassing")
                raise
    
    def _fetch_page_advanced(self, url: str, profile: Dict) -> requests.Response:
        """Advanced page fetching with multiple bypass techniques"""
        for attempt in range(config.scraping.max_retries + 2):
            try:
                # Calculate progressive delay with jitter
                if attempt > 0:
                    base_delay = config.scraping.retry_delay * (config.scraping.backoff_factor ** (attempt - 1))
                    jitter = random.uniform(0.5, 2.0)
                    delay = base_delay + jitter
                    
                    self.logger.info(f"Waiting {delay:.1f}s before attempt {attempt + 1}")
                    time.sleep(delay)
                
                # Rotate browser profile on retry
                if attempt > 0:
                    profile = self._get_current_browser_profile()
                    self._set_advanced_headers(url, profile)
                    self.logger.info(f"Switched to browser profile: {profile['name']}")
                
                # Add pre-request noise
                self._add_browser_noise()
                
                # Random delay before actual request
                pre_request_delay = random.uniform(0.1, 0.8)
                time.sleep(pre_request_delay)
                
                self.logger.info(f"Attempt {attempt + 1} for {url} using {profile['name']}")
                
                # Make the request
                response = self.session.get(
                    url,
                    timeout=config.scraping.timeout + random.uniform(0, 5),  # Random timeout variance
                    allow_redirects=True,
                    stream=False  # Don't stream for better compatibility
                )
                
                # Check response
                if response.status_code == 200:
                    # Add post-request delay to simulate reading time
                    reading_time = random.uniform(2.0, 5.0)
                    time.sleep(reading_time)
                    return response
                
                elif response.status_code == 403:
                    self.logger.warning(f"403 Forbidden on attempt {attempt + 1}")
                    # Don't immediately fail, try different techniques
                    
                elif response.status_code in [429, 503, 504]:
                    # Rate limited or server error - wait longer
                    wait_time = random.uniform(10, 20)
                    self.logger.warning(f"Rate limited/server error, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                
                if attempt < config.scraping.max_retries + 1:
                    continue
                else:
                    # Final attempt with most aggressive techniques
                    return self._final_attempt_aggressive(url, profile)
        
        # If we get here, all attempts failed
        raise Exception(f"Failed to fetch {url} after all attempts")
    
    def _handle_403_advanced(self, url: str, profile: Dict) -> requests.Response:
        """Handle 403 with advanced techniques"""
        self.logger.info("Attempting advanced 403 bypass techniques")
        
        techniques = [
            self._try_mobile_user_agent,
            self._try_minimal_headers,
            self._try_different_accept_headers,
            self._try_older_browser_version,
            self._try_referrer_spoofing
        ]
        
        for i, technique in enumerate(techniques):
            try:
                self.logger.info(f"Trying technique {i+1}: {technique.__name__}")
                response = technique(url, profile)
                if response and response.status_code == 200:
                    return response
            except Exception as e:
                self.logger.debug(f"Technique {technique.__name__} failed: {e}")
                continue
        
        # If all techniques fail, make one final attempt
        return self._final_attempt_aggressive(url, profile)
    
    def _try_mobile_user_agent(self, url: str, profile: Dict) -> Optional[requests.Response]:
        """Try with mobile user agent"""
        mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
        self.session.headers.update({'User-Agent': mobile_ua})
        return self.session.get(url, timeout=config.scraping.timeout)
    
    def _try_minimal_headers(self, url: str, profile: Dict) -> Optional[requests.Response]:
        """Try with minimal headers"""
        minimal_headers = {
            'User-Agent': profile['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        self.session.headers.clear()
        self.session.headers.update(minimal_headers)
        return self.session.get(url, timeout=config.scraping.timeout)
    
    def _try_different_accept_headers(self, url: str, profile: Dict) -> Optional[requests.Response]:
        """Try with different Accept headers"""
        self.session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        })
        return self.session.get(url, timeout=config.scraping.timeout)
    
    def _try_older_browser_version(self, url: str, profile: Dict) -> Optional[requests.Response]:
        """Try with older browser version"""
        old_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        self.session.headers.update({'User-Agent': old_ua})
        return self.session.get(url, timeout=config.scraping.timeout)
    
    def _try_referrer_spoofing(self, url: str, profile: Dict) -> Optional[requests.Response]:
        """Try with spoofed referrer"""
        common_referrers = [
            'https://www.google.com/',
            'https://www.bing.com/',
            'https://duckduckgo.com/',
            'https://www.yahoo.com/',
            'https://www.facebook.com/',
            'https://t.co/'
        ]
        self.session.headers.update({'Referer': random.choice(common_referrers)})
        return self.session.get(url, timeout=config.scraping.timeout)
    
    def _final_attempt_aggressive(self, url: str, profile: Dict) -> requests.Response:
        """Final attempt with most aggressive techniques"""
        self.logger.info("Making final aggressive attempt")
        
        # Clear all headers and start fresh
        self.session.headers.clear()
        
        # Use most basic headers possible
        basic_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }
        self.session.headers.update(basic_headers)
        
        # Long wait to simulate human behavior
        time.sleep(random.uniform(5, 10))
        
        try:
            response = self.session.get(url, timeout=config.scraping.timeout * 2)
            response.raise_for_status()
            return response
        except Exception as e:
            self.logger.error(f"All bypass attempts failed: {e}")
            raise
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _get_url_hash(self, url: str) -> str:
        """Generate hash for URL caching"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear the scraping cache"""
        self.cache.clear()
        self.logger.info("Scraping cache cleared")
    
    def get_cache_size(self) -> int:
        """Get the current cache size"""
        return len(self.cache)
    
    def _detect_encoding(self, response: requests.Response) -> str:
        """Detect the correct encoding for the response"""
        # Try to get encoding from response headers
        if response.encoding and response.encoding.lower() != 'iso-8859-1':
            return response.encoding
        
        # Use chardet to detect encoding
        detected = chardet.detect(response.content)
        if detected and detected['confidence'] > 0.8 and detected.get('encoding'):
            encoding = detected.get('encoding')
            return encoding if encoding else 'utf-8'
        
        # Default to utf-8
        return 'utf-8'
    
    def _extract_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract content using multiple strategies"""
        
        # Remove unwanted elements
        self._remove_unwanted_elements(soup)
        
        # Strategy 1: Look for semantic content containers
        content = self._extract_semantic_content(soup)
        
        # Strategy 2: Fallback to paragraph extraction
        if not content or len(content.strip()) < 100:
            self.logger.info("Semantic extraction failed, trying paragraph extraction")
            content = self._extract_paragraph_content(soup)
        
        # Strategy 3: Fallback to newspaper3k if available
        if not content or len(content.strip()) < 100:
            self.logger.info("Paragraph extraction failed, trying newspaper3k")
            content = self._extract_with_newspaper(url)
        
        # If all strategies fail, extract all text
        if not content or len(content.strip()) < 50:
            self.logger.warning("All extraction strategies failed, using basic text extraction")
            content = soup.get_text(separator=' ', strip=True)
        
        # Extract metadata
        title = self._extract_title(soup)
        author = self._extract_author(soup)
        publish_date = self._extract_publish_date(soup)
        description = self._extract_description(soup)
        
        return {
            'title': title,
            'author': author,
            'publish_date': publish_date,
            'description': description,
            'content': content.strip(),
            'word_count': len(content.split()) if content else 0,
            'extraction_method': 'advanced_multi_strategy'
        }
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove unwanted elements from the soup"""
        for selector in UNWANTED_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
    
    def _extract_semantic_content(self, soup: BeautifulSoup) -> str:
        """Extract content using semantic selectors"""
        for selector in CONTENT_SELECTORS:
            elements = soup.select(selector)
            if elements:
                content_parts = []
                for element in elements:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 50:  # Only include substantial content
                        content_parts.append(text)
                
                if content_parts:
                    content = ' '.join(content_parts)
                    self.logger.info(f"Content extracted using selector: {selector}")
                    return content
        
        return ""
    
    def _extract_paragraph_content(self, soup: BeautifulSoup) -> str:
        """Extract content from paragraphs"""
        paragraphs = soup.find_all(['p', 'div', 'span'])
        content_parts = []
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) >= config.processing.min_paragraph_length:
                content_parts.append(text)
        
        return ' '.join(content_parts)
    
    def _extract_with_newspaper(self, url: str) -> str:
        """Extract content using newspaper3k library"""
        try:
            from newspaper import Article
            article = Article(url)
            article.download()
            article.parse()
            return article.text
        except ImportError:
            self.logger.debug("newspaper3k not available")
            return ""
        except Exception as e:
            self.logger.debug(f"newspaper3k extraction failed: {e}")
            return ""
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the article title"""
        # Try multiple title selectors
        title_selectors = [
            'h1',
            'title',
            '[property="og:title"]',
            '[name="twitter:title"]',
            '.title',
            '.headline',
            '.post-title',
            '.article-title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True) or str(element.get('content', ''))
                if title and len(title) > 5:
                    return title
        
        return "Unknown Title"
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract the article author"""
        author_selectors = [
            '[name="author"]',
            '[property="article:author"]',
            '[rel="author"]',
            '.author',
            '.byline',
            '.writer'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = element.get_text(strip=True) or str(element.get('content', ''))
                if author:
                    return author
        
        return "Unknown Author"
    
    def _extract_publish_date(self, soup: BeautifulSoup) -> str:
        """Extract the publish date"""
        date_selectors = [
            '[property="article:published_time"]',
            '[name="publish_date"]',
            '[name="date"]',
            'time[datetime]',
            '.date',
            '.publish-date',
            '.timestamp'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date = str(element.get('content', '')) or str(element.get('datetime', '')) or element.get_text(strip=True)
                if date:
                    return date
        
        return "Unknown Date"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract the article description"""
        desc_selectors = [
            '[name="description"]',
            '[property="og:description"]',
            '[name="twitter:description"]',
            '.description',
            '.excerpt',
            '.summary'
        ]
        
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                description = str(element.get('content', '')) or element.get_text(strip=True)
                if description and len(description) > 10:
                    return description
        
        return "No description available"
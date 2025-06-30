"""
Advanced Selenium Scraper Module for Article Summarizer Agent
Uses browser automation to bypass sophisticated WAF protections
100% FREE - No paid services required
"""

import logging
import time
import random
import json
import os
import tempfile
from typing import Dict, Optional, List, Tuple
from urllib.parse import urlparse
from pathlib import Path

# Selenium and browser automation
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    import undetected_chromedriver as uc
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Additional tools
try:
    from fake_useragent import UserAgent
    import cloudscraper
    import psutil
    ADDITIONAL_TOOLS_AVAILABLE = True
except ImportError:
    ADDITIONAL_TOOLS_AVAILABLE = False

from bs4 import BeautifulSoup
from config import config

class AdvancedSeleniumScraper:
    """Advanced scraper using Selenium with sophisticated WAF bypassing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium dependencies not available. Install with: pip install selenium webdriver-manager undetected-chromedriver")
        
        self.driver = None
        self.user_agent_generator = UserAgent() if ADDITIONAL_TOOLS_AVAILABLE else None
        self.temp_profile_dir = None
        self._setup_browser_profiles()
        
    def _setup_browser_profiles(self):
        """Setup browser profiles for maximum stealth"""
        self.browser_profiles = [
            {
                'name': 'stealth_chrome_windows',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'platform': 'Win32',
                'languages': ['en-US', 'en'],
                'viewport': {'width': 1920, 'height': 1080},
                'timezone': 'America/New_York'
            },
            {
                'name': 'stealth_chrome_mac',
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'platform': 'MacIntel',
                'languages': ['en-US', 'en'],
                'viewport': {'width': 1440, 'height': 900},
                'timezone': 'America/Los_Angeles'
            },
            {
                'name': 'stealth_chrome_linux',
                'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'platform': 'Linux x86_64',
                'languages': ['en-US', 'en'],
                'viewport': {'width': 1920, 'height': 1080},
                'timezone': 'America/Chicago'
            }
        ]
    
    def _create_stealth_driver(self, profile: Dict):
        """Create a highly stealthed Chrome driver"""
        self.logger.info(f"Creating stealth driver with profile: {profile['name']}")
        
        # Create temporary profile directory
        self.temp_profile_dir = tempfile.mkdtemp(prefix='chrome_profile_')
        
        # Advanced Chrome options for maximum stealth
        options = uc.ChromeOptions()
        
        # Basic stealth options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # Faster loading
        options.add_argument('--disable-java')
        options.add_argument('--disable-flash')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-default-apps')
        
        # Advanced anti-detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Fingerprinting evasion
        options.add_argument(f'--user-agent={profile["user_agent"]}')
        options.add_argument(f'--user-data-dir={self.temp_profile_dir}')
        options.add_argument(f'--window-size={profile["viewport"]["width"]},{profile["viewport"]["height"]}')
        
        # Language and locale
        options.add_argument(f'--lang={profile["languages"][0]}')
        options.add_argument(f'--accept-lang={",".join(profile["languages"])}')
        
        # Memory and performance optimizations
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        # Additional stealth headers
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        try:
            # Try undetected-chromedriver first (best for WAF bypassing)
            driver = uc.Chrome(options=options, version_main=None)
            self.logger.info("Successfully created undetected Chrome driver")
        except Exception as e:
            self.logger.warning(f"Undetected Chrome failed: {e}, falling back to regular Chrome")
            try:
                # Fallback to regular Chrome
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception as e2:
                self.logger.error(f"Regular Chrome also failed: {e2}")
                raise
        
        # Execute advanced stealth scripts
        self._apply_stealth_scripts(driver, profile)
        
        return driver
    
    def _apply_stealth_scripts(self, driver, profile: Dict):
        """Apply advanced JavaScript stealth techniques"""
        
        # Remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Modify navigator properties
        stealth_script = f"""
        // Override navigator properties
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{profile["platform"]}'
        }});
        
        Object.defineProperty(navigator, 'languages', {{
            get: () => {json.dumps(profile["languages"])}
        }});
        
        Object.defineProperty(navigator, 'language', {{
            get: () => '{profile["languages"][0]}'
        }});
        
        // Override screen properties
        Object.defineProperty(screen, 'width', {{
            get: () => {profile["viewport"]["width"]}
        }});
        
        Object.defineProperty(screen, 'height', {{
            get: () => {profile["viewport"]["height"]}
        }});
        
        Object.defineProperty(screen, 'availWidth', {{
            get: () => {profile["viewport"]["width"]}
        }});
        
        Object.defineProperty(screen, 'availHeight', {{
            get: () => {profile["viewport"]["height"] - 40}
        }});
        
        // Mock timezone
        Date.prototype.getTimezoneOffset = function() {{
            return {self._get_timezone_offset(profile["timezone"])};
        }};
        
        // Hide automation indicators
        Object.defineProperty(navigator, 'permissions', {{
            get: () => ({{
                query: () => Promise.resolve({{ state: 'granted' }})
            }})
        }});
        
        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [
                {{
                    name: 'Chrome PDF Plugin',
                    filename: 'internal-pdf-viewer',
                    description: 'Portable Document Format'
                }},
                {{
                    name: 'Chrome PDF Viewer',
                    filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                    description: ''
                }}
            ]
        }});
        
        // Mock WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel(R) HD Graphics 620';
            return getParameter.call(this, parameter);
        }};
        
        // Remove common automation detection
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """
        
        driver.execute_script(stealth_script)
        
        # Set additional stealth properties
        driver.execute_cdp_cmd('Runtime.evaluate', {
            'expression': '''
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4
                });
                
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
            '''
        })
    
    def _get_timezone_offset(self, timezone: str) -> int:
        """Get timezone offset for spoofing"""
        timezone_offsets = {
            'America/New_York': 300,
            'America/Los_Angeles': 480,
            'America/Chicago': 360,
            'Europe/London': 0,
            'Europe/Paris': -60
        }
        return timezone_offsets.get(timezone, 0)
    
    def scrape_with_selenium(self, url: str, wait_time: int = 30) -> Dict:
        """Main scraping method using Selenium with advanced WAF bypassing"""
        self.logger.info(f"Starting Selenium scraping for: {url}")
        
        # Choose random profile
        profile = random.choice(self.browser_profiles)
        
        try:
            # Create stealth driver
            self.driver = self._create_stealth_driver(profile)
            
            # Navigate with human-like behavior
            success = self._navigate_like_human(url, wait_time)
            
            if not success:
                raise Exception("Failed to load page after all attempts")
            
            # Handle potential challenges
            self._handle_challenges()
            
            # Extract content
            content_data = self._extract_content_selenium()
            
            # Add metadata
            content_data.update({
                'url': url,
                'scraping_method': 'selenium_advanced',
                'browser_profile': profile['name'],
                'scraped_at': time.time()
            })
            
            self.logger.info(f"Successfully scraped with Selenium: {content_data.get('title', 'Unknown')}")
            return content_data
            
        except Exception as e:
            self.logger.error(f"Selenium scraping failed: {e}")
            # Try cloudscraper as fallback
            return self._fallback_cloudscraper(url)
        
        finally:
            self._cleanup()
    
    def _navigate_like_human(self, url: str, wait_time: int) -> bool:
        """Navigate to URL with human-like behavior patterns"""
        
        try:
            # First, visit a common site (like Google) to establish session
            self.logger.info("Establishing session with google.com...")
            self.driver.get("https://www.google.com")
            time.sleep(random.uniform(2, 4))
            
            # Simulate some human activity
            self._simulate_human_activity()
            
            # Navigate to target URL
            self.logger.info(f"Navigating to target URL: {url}")
            self.driver.get(url)
            
            # Wait for page load with timeout
            wait = WebDriverWait(self.driver, wait_time)
            
            # Check for common indicators that page loaded
            try:
                wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                time.sleep(random.uniform(3, 6))  # Additional wait for dynamic content
                return True
                
            except TimeoutException:
                self.logger.warning("Page load timeout, but continuing...")
                return True
                
        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")
            return False
    
    def _simulate_human_activity(self):
        """Simulate realistic human behavior on Google"""
        try:
            # Find search box and simulate typing
            search_box = self.driver.find_element(By.NAME, "q")
            
            # Type something realistic
            search_terms = ["news", "technology", "articles", "information"]
            search_term = random.choice(search_terms)
            
            # Type with human-like delays
            for char in search_term:
                search_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            time.sleep(random.uniform(1, 2))
            
            # Clear the search box
            search_box.clear()
            time.sleep(random.uniform(0.5, 1))
            
            # Simulate mouse movement
            actions = ActionChains(self.driver)
            for _ in range(3):
                x_offset = random.randint(-100, 100)
                y_offset = random.randint(-100, 100)
                actions.move_by_offset(x_offset, y_offset)
                time.sleep(random.uniform(0.1, 0.3))
            actions.perform()
            
        except Exception as e:
            self.logger.debug(f"Human simulation failed (non-critical): {e}")
    
    def _handle_challenges(self):
        """Handle various challenges (Cloudflare, CAPTCHA, etc.)"""
        
        # Check for Cloudflare challenge
        if self._detect_cloudflare_challenge():
            self._handle_cloudflare_challenge()
        
        # Check for CAPTCHA
        if self._detect_captcha():
            self._handle_captcha()
        
        # Check for access denied
        if self._detect_access_denied():
            self._handle_access_denied()
    
    def _detect_cloudflare_challenge(self) -> bool:
        """Detect Cloudflare challenge page"""
        page_source = self.driver.page_source.lower()
        cloudflare_indicators = [
            'checking your browser',
            'cloudflare',
            'just a moment',
            'please wait',
            'security check',
            'ddos protection'
        ]
        return any(indicator in page_source for indicator in cloudflare_indicators)
    
    def _handle_cloudflare_challenge(self):
        """Handle Cloudflare challenge automatically"""
        self.logger.info("Cloudflare challenge detected, waiting for resolution...")
        
        # Wait for challenge to resolve (usually 5-10 seconds)
        max_wait = 60
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Check if challenge is resolved
            if not self._detect_cloudflare_challenge():
                self.logger.info("Cloudflare challenge resolved!")
                return
            
            # Simulate minimal human activity during wait
            try:
                actions = ActionChains(self.driver)
                actions.move_by_offset(random.randint(-10, 10), random.randint(-10, 10))
                actions.perform()
            except:
                pass
            
            time.sleep(2)
        
        self.logger.warning("Cloudflare challenge did not resolve automatically")
    
    def _detect_captcha(self) -> bool:
        """Detect CAPTCHA presence"""
        page_source = self.driver.page_source.lower()
        captcha_indicators = [
            'captcha', 'recaptcha', 'hcaptcha', 'turnstile',
            'verify you are human', 'prove you are not a robot'
        ]
        return any(indicator in page_source for indicator in captcha_indicators)
    
    def _handle_captcha(self):
        """Handle CAPTCHA (placeholder for future implementation)"""
        self.logger.warning("CAPTCHA detected - manual intervention may be required")
        # In a production environment, you could integrate with CAPTCHA solving services
        # For now, we'll wait and hope it resolves automatically
        time.sleep(10)
    
    def _detect_access_denied(self) -> bool:
        """Detect access denied pages"""
        page_source = self.driver.page_source.lower()
        denied_indicators = [
            'access denied', 'forbidden', '403', 'blocked',
            'you do not have permission', 'unauthorized'
        ]
        return any(indicator in page_source for indicator in denied_indicators)
    
    def _handle_access_denied(self):
        """Handle access denied by refreshing with new fingerprint"""
        self.logger.warning("Access denied detected, attempting refresh...")
        
        # Change user agent
        if self.user_agent_generator:
            new_ua = self.user_agent_generator.random
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                'userAgent': new_ua
            })
        
        # Wait and refresh
        time.sleep(random.uniform(5, 10))
        self.driver.refresh()
        time.sleep(random.uniform(3, 6))
    
    def _extract_content_selenium(self) -> Dict:
        """Extract content using Selenium"""
        
        # Get page source
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Use existing extraction logic
        from .web_scraper import WebScraper
        extractor = WebScraper()
        
        # Remove unwanted elements
        extractor._remove_unwanted_elements(soup)
        
        # Extract content
        content = extractor._extract_semantic_content(soup)
        
        if not content or len(content.strip()) < 100:
            content = extractor._extract_paragraph_content(soup)
        
        if not content or len(content.strip()) < 50:
            content = soup.get_text(separator=' ', strip=True)
        
        # Extract metadata
        title = extractor._extract_title(soup)
        author = extractor._extract_author(soup)
        publish_date = extractor._extract_publish_date(soup)
        description = extractor._extract_description(soup)
        
        return {
            'title': title,
            'author': author,
            'publish_date': publish_date,
            'description': description,
            'content': content.strip(),
            'word_count': len(content.split()) if content else 0,
            'extraction_method': 'selenium_advanced'
        }
    
    def _fallback_cloudscraper(self, url: str) -> Dict:
        """Fallback using cloudscraper library"""
        if not ADDITIONAL_TOOLS_AVAILABLE:
            raise Exception("Both Selenium and cloudscraper failed")
        
        self.logger.info("Attempting cloudscraper fallback...")
        
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )
            
            response = scraper.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic content
            title = soup.title.get_text(strip=True) if soup.title else "Unknown Title"
            content = soup.get_text(separator=' ', strip=True)
            
            return {
                'title': title,
                'author': "Unknown Author",
                'publish_date': "Unknown Date",
                'description': "No description available",
                'content': content,
                'word_count': len(content.split()) if content else 0,
                'extraction_method': 'cloudscraper_fallback',
                'url': url,
                'scraped_at': time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Cloudscraper fallback also failed: {e}")
            raise
    
    def _cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        # Clean up temporary profile directory
        if self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_profile_dir)
            except:
                pass
    
    def __del__(self):
        """Ensure cleanup on destruction"""
        self._cleanup()

class SeleniumIntegrationMixin:
    """Mixin to integrate Selenium capabilities into existing WebScraper"""
    
    def __init__(self):
        super().__init__()
        self.selenium_scraper = None
        if SELENIUM_AVAILABLE:
            try:
                self.selenium_scraper = AdvancedSeleniumScraper()
                self.logger.info("Selenium integration enabled")
            except Exception as e:
                self.logger.warning(f"Selenium integration failed: {e}")
    
    def scrape_with_selenium_fallback(self, url: str) -> Dict:
        """Try regular scraping first, then Selenium if needed"""
        
        try:
            # Try regular scraping first
            result = super().scrape_article(url)
            self.logger.info("Regular scraping successful")
            return result
            
        except Exception as e:
            self.logger.warning(f"Regular scraping failed: {e}")
            
            # Try Selenium as fallback
            if self.selenium_scraper:
                self.logger.info("Attempting Selenium fallback...")
                try:
                    return self.selenium_scraper.scrape_with_selenium(url)
                except Exception as selenium_error:
                    self.logger.error(f"Selenium fallback also failed: {selenium_error}")
                    raise
            else:
                raise Exception("Both regular scraping and Selenium unavailable") 
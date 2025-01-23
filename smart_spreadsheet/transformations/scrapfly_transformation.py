import logging
import re
from urllib.parse import urlparse, urlunparse
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup, SoupStrainer
from transformations.base import BaseTransformation
import pandas as pd
logger = logging.getLogger(__name__)

class StealthBrowserScraper:
    def __init__(self):
        self.browser_args = {
            "headless": True,
            "timeout": 60000
        }
        self.text_tags = SoupStrainer(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                                      'li', 'article', 'section', 'div', 'span'])

    def clean_and_validate_url(self, url):
        """Clean and validate URL format without external dependencies"""
        if not isinstance(url, str) or not url.strip():
            return None

        # Basic cleaning
        url = url.strip().replace(' ', '%20')
        
        # Parse URL components
        parsed = urlparse(url)
        
        # Add scheme if missing
        if not parsed.scheme:
            url = f'http://{url}'
            parsed = urlparse(url)
        
        # Force HTTP scheme if not HTTPS
        if parsed.scheme not in ('http', 'https'):
            parsed = parsed._replace(scheme='http')
            url = urlunparse(parsed)
        
        # Validate network location
        if not parsed.netloc:
            return None
        
        # Basic domain format validation
        netloc = parsed.netloc.split(':')[0]  # Remove port if present
        if not re.match(r'^(localhost|([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})$', netloc):
            return None
        
        # Rebuild proper URL
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

    def _sanitize_html(self, html):
        """Clean HTML before text extraction"""
        soup = BeautifulSoup(html, 'lxml', parse_only=self.text_tags)
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'noscript', 'meta', 'link', 
                            'header', 'footer', 'nav', 'form', 'button']):
            element.decompose()
            
        return soup

    def extract_clean_text(self, html):
        """Extract and clean text content using BeautifulSoup"""
        try:
            soup = self._sanitize_html(html)
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up text
            text = re.sub(r'\n{3,}', '\n\n', text)  # Reduce multiple newlines
            text = re.sub(r'[ \t]{2,}', ' ', text)  # Reduce multiple spaces
            return text.strip()
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return None

    def fetch_text_content(self, url):
        cleaned_url = self.clean_and_validate_url(url)
        if not cleaned_url:
            return None

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(**self.browser_args)
                context = browser.new_context()
                page = context.new_page()
                
                stealth_sync(page)
                
                try:
                    page.goto(cleaned_url, wait_until="networkidle", timeout=15000)
                    html = page.content()
                finally:
                    browser.close()
                
                return self.extract_clean_text(html)
                
        except Exception as e:
            logger.error(f"Browser failed for {cleaned_url}: {str(e)}")
            return None


class StealthBrowserTransformation(BaseTransformation):
    name = "Stealth Browser Web Scraper"
    description = "Extracts webpage text using headless browser with URL validation and anti-detection"

    def required_inputs(self):
        return ["URL Column"]

    def transform(self, df, output_col_name, *args):
        url_col = args[0]
        scraper = StealthBrowserScraper()

        def scrape_row(row):
            url = row[url_col]
            return scraper.fetch_text_content(url) if pd.notna(url) else None

        df[output_col_name] = df.apply(scrape_row, axis=1)
        return df
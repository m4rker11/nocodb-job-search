import logging
import os
from scrapfly import ScrapflyClient, ScrapeConfig
from transformations.base import BaseTransformation

logger = logging.getLogger(__name__)

class SimpleWebScraper:
    def __init__(self):
        self.scrapfly = ScrapflyClient(
            key=os.environ.get("SCRAPFLY_API_KEY", ""),
            max_concurrency=2,
        )

    def fetch_text_content(self, url):
        # Try without JS rendering first
        text_content = self._fetch_content(url, render_js=False)
        if text_content is None:
            logger.info(f"[Scrapfly] Retrying {url} with JS rendering.")
            text_content = self._fetch_content(url, render_js=True)

        if text_content:
            return text_content.strip()
        else:
            logger.error(f"[Scrapfly] Failed to scrape {url}")
            return None

    def _fetch_content(self, url, render_js):
        try:
            scrape_config = ScrapeConfig(
                url=url,
                render_js=render_js,
                country="us",
                cache=True,
                retry=True,
                format="text"
            )
            response = self.scrapfly.scrape(scrape_config)
            if response.success:
                return response.scrape_result.get("content")
            else:
                logger.error(f"[Scrapfly] Non-success status for {url}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"[Scrapfly] Exception fetching {url}: {str(e)}")
            return None

class ScrapflyWebScraperTransformation(BaseTransformation):
    name = "Scrapfly Web Scraper Transformation"
    description = "Scrapes website content for each row’s URL using Scrapfly and stores the extracted text."

    def required_inputs(self):
        return ["URL Column"]

    def transform(self, df, output_col_name, *args):
        url_col = args[0]
        scraper = SimpleWebScraper()

        def scrape_row(row):
            url = row[url_col]
            if not url:
                return None
            return scraper.fetch_text_content(url)

        df[output_col_name] = df.apply(scrape_row, axis=1)
        return df

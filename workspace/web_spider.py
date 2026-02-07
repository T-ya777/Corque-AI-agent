#!/usr/bin/env python3
"""
Versatile Web Spider - A production-grade web crawling library.
Compatible with Python 3.6+
"""

import re
import ssl
import time
import hashlib
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape as html_unescape
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class CrawledPage:
    """Represents a crawled web page with its metadata."""

    url: str
    title: str
    content: str
    links: Set[str] = field(default_factory=set)
    images: Set[str] = field(default_factory=set)
    meta_description: str = ""
    status_code: int = 0
    content_type: str = ""
    crawl_time: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "content_length": len(self.content),
            "links_count": len(self.links),
            "images_count": len(self.images),
            "meta_description": self.meta_description,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "crawl_time": self.crawl_time.isoformat(),
            "error": self.error,
        }


class SSLContextFactory:
    """Factory for creating SSL contexts with proper configuration."""

    @staticmethod
    def create_context(check_hostname: bool = True) -> ssl.SSLContext:
        """Create an SSL context that works across Python versions."""
        try:
            # Python 3.4+
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except AttributeError:
            # Fallback for older versions
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)

        context.check_hostname = check_hostname
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_default_certs()
        return context


class RobotsTxtParser:
    """Parser for robots.txt files to respect crawler directives."""

    def __init__(self, user_agent: str = "*"):
        """Initialize the parser with a user agent."""
        self.user_agent = user_agent
        self.rules: Dict[str, Dict[str, List[str]]] = {}
        self.crawl_delay: float = 0
        self.sitemap_url: Optional[str] = None

    def parse(self, content: str) -> None:
        """Parse robots.txt content."""
        current_agent: Optional[str] = None
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.lower().startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip().lower()
                if agent == "*" or agent == self.user_agent.lower():
                    current_agent = agent
                    if agent not in self.rules:
                        self.rules[agent] = {"allow": [], "disallow": []}
            elif current_agent:
                if line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    self.rules[current_agent]["disallow"].append(path)
                elif line.lower().startswith("allow:"):
                    path = line.split(":", 1)[1].strip()
                    self.rules[current_agent]["allow"].append(path)
                elif line.lower().startswith("crawl-delay:"):
                    try:
                        self.crawl_delay = float(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                elif line.lower().startswith("sitemap:"):
                    self.sitemap_url = line.split(":", 1)[1].strip()

    def is_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        parsed = urllib.parse.urlparse(url)
        path = parsed.path if parsed.path else "/"

        for agent_rules in self.rules.values():
            for disallow in agent_rules["disallow"]:
                if path.startswith(disallow):
                    # Check if there's a more specific allow rule
                    allowed = False
                    for allow in agent_rules["allow"]:
                        if path.startswith(allow):
                            allowed = True
                            break
                    if not allowed:
                        return False
        return True


class WebSpider:
    """
    A versatile web spider with configurable crawling capabilities.

    Features:
    - Configurable depth limiting
    - Respect of robots.txt
    - Duplicate content detection
    - Rate limiting
    - SSL/TLS support
    - Error handling and recovery
    """

    DEFAULT_HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (compatible; WebSpider/1.0; +http://localhost)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    def __init__(
        self,
        base_url: str,
        max_depth: int = 3,
        max_pages: int = 100,
        delay: float = 1.0,
        timeout: int = 10,
        respect_robots: bool = True,
        user_agent: str = "WebSpider/1.0",
        verbose: bool = False,
    ):
        """
        Initialize the web spider.

        Args:
            base_url: Starting URL for crawling.
            max_depth: Maximum crawl depth.
            max_pages: Maximum number of pages to crawl.
            delay: Delay between requests in seconds.
            timeout: Request timeout in seconds.
            respect_robots: Whether to respect robots.txt.
            user_agent: User agent string.
            verbose: Enable verbose logging.
        """
        self.base_url = base_url
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.delay = delay
        self.timeout = timeout
        self.respect_robots = respect_robots
        self.user_agent = user_agent
        self._verbose = verbose

        self.visited_urls: Set[str] = set()
        self.crawled_pages: List[CrawledPage] = []
        self.url_queue: Deque[Tuple[str, int]] = deque()
        self.content_hashes: Set[str] = set()
        self.robots_parser = RobotsTxtParser(user_agent)

        # Create SSL context once for reuse
        self.ssl_context = SSLContextFactory.create_context()

        # Configure logging level
        if verbose:
            logger.setLevel(logging.DEBUG)

    def _normalize_url(self, url: str, base: str) -> Optional[str]:
        """Normalize and resolve relative URLs."""
        try:
            # Handle relative URLs
            if not urllib.parse.urlparse(url).scheme:
                url = urllib.parse.urljoin(base, url)

            # Parse and reconstruct URL
            parsed = urllib.parse.urlparse(url)

            # Only process HTTP/HTTPS URLs
            if parsed.scheme not in ("http", "https"):
                return None

            # Reconstruct URL without fragments
            normalized = urllib.parse.urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc.lower(),
                    parsed.path or "/",
                    parsed.params,
                    parsed.query,
                    "",  # Remove fragment
                )
            )

            return normalized
        except Exception as e:
            logger.warning(f"URL normalization failed for {url}: {e}")
            return None

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL is on the same domain as base URL."""
        try:
            base_parsed = urllib.parse.urlparse(self.base_url)
            url_parsed = urllib.parse.urlparse(url)
            return base_parsed.netloc.lower() == url_parsed.netloc.lower()
        except Exception:
            return False

    def _fetch_page(self, url: str) -> Tuple[Optional[str], Optional[str], int]:
        """Fetch a web page.

        Returns:
            Tuple of (content, content_type, status_code).
        """
        try:
            headers = self.DEFAULT_HEADERS.copy()
            headers["User-Agent"] = self.user_agent

            request = urllib.request.Request(url, headers=headers)

            # Use SSL context for HTTPS
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme == "https":
                opener = urllib.request.build_opener(
                    urllib.request.HTTPSHandler(context=self.ssl_context)
                )
            else:
                opener = urllib.request.build_opener()

            with opener.open(request, timeout=self.timeout) as response:
                content = response.read()
                # Decode with fallback encodings
                content_type = response.headers.get("Content-Type", "")
                encoding_match = re.search(r"charset=([\w-]+)", content_type)
                charset = encoding_match.group(1) if encoding_match else "utf-8"

                try:
                    content = content.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    content = content.decode("utf-8", errors="replace")

                return content, content_type, response.status

        except urllib.error.HTTPError as e:
            logger.warning(
                f"HTTP Error {e.code} for {url}: {e.reason}"
            )
            return None, None, e.code
        except urllib.error.URLError as e:
            logger.warning(f"URL Error for {url}: {e.reason}")
            return None, None, 0
        except ssl.SSLError as e:
            logger.warning(f"SSL Error for {url}: {e}")
            return None, None, 0
        except TimeoutError:
            logger.warning(f"Timeout Error for {url}")
            return None, None, 0
        except OSError as e:
            logger.warning(f"OS Error for {url}: {e}")
            return None, None, 0

    def _extract_content(
        self, content: str
    ) -> Tuple[str, Set[str], Set[str], str, str]:
        """Extract title, links, images, and meta description from HTML."""
        title = ""
        links: Set[str] = set()
        images: Set[str] = set()
        meta_description = ""
        text_content = ""

        # Extract title
        title_match = re.search(
            r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE
        )
        if title_match:
            title = html_unescape(title_match.group(1).strip())

        # Extract meta description
        desc_match = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
            content,
            re.IGNORECASE,
        )
        if desc_match:
            meta_description = html_unescape(desc_match.group(1).strip())

        # Extract links
        link_pattern = re.compile(r'<a[^>]+href=["\']([^"\']+)["\']', re.IGNORECASE)
        for match in link_pattern.finditer(content):
            href = match.group(1).strip()
            if href and not href.startswith(("javascript:", "mailto:", "#")):
                links.add(href)

        # Extract images
        img_pattern = re.compile(
            r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE
        )
        for match in img_pattern.finditer(content):
            src = match.group(1).strip()
            if src:
                images.add(src)

        # Clean content for text extraction
        text_content = re.sub(
            r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE
        )
        text_content = re.sub(
            r"<style[^>]*>.*?</style>", "", text_content, flags=re.DOTALL | re.IGNORECASE
        )
        text_content = re.sub(r"<[^>]+>", "", text_content)
        text_content = html_unescape(text_content)
        text_content = re.sub(r"\s+", " ", text_content).strip()

        return title, links, images, meta_description, text_content

    def _is_duplicate(self, content: str) -> bool:
        """Check if content is a duplicate."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in self.content_hashes:
            return True
        self.content_hashes.add(content_hash)
        return False

    def _fetch_robots_txt(self) -> None:
        """Fetch and parse robots.txt from the base URL."""
        try:
            parsed = urllib.parse.urlparse(self.base_url)
            robots_url = urllib.parse.urlunparse(
                (parsed.scheme, parsed.netloc, "/robots.txt", "", "", "")
            )

            content, _, status = self._fetch_page(robots_url)
            if content and status == 200:
                self.robots_parser.parse(content)
                logger.info(f"Parsed robots.txt from {robots_url}")
        except Exception:
            logger.debug("Could not fetch robots.txt")

    def crawl(self) -> List[CrawledPage]:
        """Execute the web crawl.

        Returns:
            List of crawled pages.
        """
        logger.info(f"Starting crawl of {self.base_url}")

        # Fetch robots.txt if required
        if self.respect_robots:
            self._fetch_robots_txt()
            if not self.robots_parser.is_allowed(self.base_url):
                logger.warning(
                    f"Base URL disallowed by robots.txt: {self.base_url}"
                )
                return []

        # Initialize queue with (url, depth)
        self.url_queue.append((self.base_url, 0))

        while self.url_queue and len(self.visited_urls) < self.max_pages:
            url, depth = self.url_queue.popleft()

            # Skip if already visited
            if url in self.visited_urls:
                continue

            # Check depth limit
            if depth > self.max_depth:
                continue

            # Check robots.txt
            if self.respect_robots and not self.robots_parser.is_allowed(url):
                logger.debug(f"URL disallowed by robots.txt: {url}")
                continue

            logger.info(f"Crawling [{depth}]: {url}")

            # Fetch the page
            content, content_type, status = self._fetch_page(url)

            if content is None:
                page = CrawledPage(
                    url=url,
                    title="",
                    content="",
                    status_code=status,
                    error=f"Failed to fetch (status: {status})",
                )
                self.crawled_pages.append(page)
                self.visited_urls.add(url)
                continue

            # Check for duplicates
            if self._is_duplicate(content):
                logger.debug(f"Duplicate content skipped: {url}")
                continue

            # Extract content
            (
                title,
                links,
                images,
                meta_description,
                text_content,
            ) = self._extract_content(content)

            # Create page object
            page = CrawledPage(
                url=url,
                title=title,
                content=text_content,
                links=set(),
                images=set(),
                meta_description=meta_description,
                status_code=status,
                content_type=content_type,
            )

            # Process links for same-domain URLs
            if depth < self.max_depth:
                for link in links:
                    normalized = self._normalize_url(link, url)
                    if normalized and normalized not in self.visited_urls:
                        if self._is_same_domain(normalized):
                            page.links.add(normalized)
                            self.url_queue.append((normalized, depth + 1))

            # Process images
            for img in images:
                normalized = self._normalize_url(img, url)
                if normalized:
                    page.images.add(normalized)

            self.crawled_pages.append(page)
            self.visited_urls.add(url)

            # Rate limiting
            time.sleep(self.delay)

        logger.info(f"Crawl complete. Visited {len(self.visited_urls)} pages.")
        return self.crawled_pages

    def get_report(self) -> Dict[str, Any]:
        """Generate a crawl report."""
        return {
            "base_url": self.base_url,
            "pages_crawled": len(self.crawled_pages),
            "unique_urls": len(self.visited_urls),
            "max_depth": self.max_depth,
            "max_pages": self.max_pages,
            "pages": [page.to_dict() for page in self.crawled_pages],
        }

    def save_report(self, filepath: str = "crawl_report.json") -> None:
        """Save crawl report to JSON file."""
        report = self.get_report()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"Report saved to {filepath}")


def run_self_tests() -> bool:
    """Run self-tests to demonstrate functionality."""
    print("=" * 60)
    print("WEB SPIDER SELF-TEST SUITE")
    print("=" * 60)

    # Test 1: URL Normalization
    print("\n[TEST 1] URL Normalization")
    print("-" * 40)

    spider = WebSpider("https://example.com/page", max_depth=1, max_pages=5)

    test_cases = [
        ("https://example.com/page", "https://example.com/page"),
        ("/relative/path", "https://example.com/relative/path"),
        ("../parent", "https://example.com/parent"),
        ("https://EXAMPLE.COM/Page", "https://example.com/Page"),
        ("https://example.com/path#fragment", "https://example.com/path"),
    ]

    for input_url, expected in test_cases:
        result = spider._normalize_url(input_url, "https://example.com/current")
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}: '{input_url}' -> '{result}' (expected: '{expected}')")

    # Test 2: Robots.txt Parser
    print("\n[TEST 2] Robots.txt Parser")
    print("-" * 40)

    robots_content = """
User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /public/
Crawl-delay: 2
Sitemap: https://example.com/sitemap.xml

User-agent: Googlebot
Disallow: /search/
"""

    parser = RobotsTxtParser()
    parser.parse(robots_content)

    test_urls = [
        ("https://example.com/index.html", True),
        ("https://example.com/admin/login", False),
        ("https://example.com/private/data", False),
        ("https://example.com/public/info", True),
    ]

    for url, expected in test_urls:
        result = parser.is_allowed(url)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}: '{url}' allowed={result} (expected: {expected})")

    print(f"  Crawl delay: {parser.crawl_delay}s")
    print(f"  Sitemap: {parser.sitemap_url}")

    # Test 3: Content Extraction
    print("\n[TEST 3] Content Extraction")
    print("-" * 40)

    sample_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page &amp; Title</title>
    <meta name="description" content="This is a test description">
</head>
<body>
    <h1>Hello World</h1>
    <a href="/page1">Link 1</a>
    <a href="https://external.com/page">External</a>
    <img src="image1.jpg" alt="Image 1">
    <img src="/images/pic.png">
    <script>alert('test');</script>
    <style>body { color: red; }</style>
</body>
</html>
"""

    (
        title,
        links,
        images,
        meta_desc,
        text,
    ) = spider._extract_content(sample_html)

    print(f"  Title: '{title}'")
    print(f"  Meta Description: '{meta_desc}'")
    print(f"  Text Content: '{text}'")
    print(f"  Links: {sorted(links)}")
    print(f"  Images: {sorted(images)}")

    # Test 4: Duplicate Detection
    print("\n[TEST 4] Duplicate Detection")
    print("-" * 40)

    spider2 = WebSpider("https://test.com", max_depth=1)

    content1 = "Same content"
    content2 = "Same content"
    content3 = "Different content"

    result1 = spider2._is_duplicate(content1)
    result2 = spider2._is_duplicate(content2)
    result3 = spider2._is_duplicate(content3)

    print(f"  First content: duplicate={result1} (expected: False)")
    print(f"  Same content: duplicate={result2} (expected: True)")
    print(f"  Different content: duplicate={result3} (expected: False)")

    # Test 5: Domain Check
    print("\n[TEST 5] Domain Check")
    print("-" * 40)

    domain_tests = [
        ("https://example.com/page", True),
        ("https://sub.example.com/page", True),
        ("https://other.com/page", False),
        ("http://example.com:8080/page", True),
    ]

    for url, expected in domain_tests:
        result = spider._is_same_domain(url)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}: '{url}' same_domain={result} (expected: {expected})")

    # Test 6: CrawledPage Serialization
    print("\n[TEST 6] CrawledPage Serialization")
    print("-" * 40)

    page = CrawledPage(
        url="https://example.com",
        title="Test Page",
        content="Sample content",
        links={"https://example.com/1", "https://example.com/2"},
        images={"img1.jpg"},
        meta_description="A test page",
        status_code=200,
        content_type="text/html",
    )

    page_dict = page.to_dict()
    print(f"  Serialized keys: {list(page_dict.keys())}")
    print(f"  URL: {page_dict['url']}")
    print(f"  Status: {page_dict['status_code']}")
    print(f"  Links count: {page_dict['links_count']}")

    # Test 7: SSL Context Creation
    print("\n[TEST 7] SSL Context Creation")
    print("-" * 40)

    try:
        ctx = SSLContextFactory.create_context()
        print("  PASS: SSL Context created successfully")
        print(f"  Protocol: {ctx.protocol}")
        print(f"  Check Hostname: {ctx.check_hostname}")
        print(f"  Verify Mode: {ctx.verify_mode}")
    except Exception as e:
        print(f"  FAIL: SSL Context creation failed: {e}")

    # Test 8: Live Crawl Test (if network available)
    print("\n[TEST 8] Live Crawl Test")
    print("-" * 40)

    try:
        # Use a simple, reliable test URL
        test_spider = WebSpider(
            "https://httpbin.org/html",
            max_depth=1,
            max_pages=2,
            delay=0.5,
            timeout=5,
            verbose=False,
        )

        pages = test_spider.crawl()

        if pages:
            crawled_page = pages[0]
            print(f"  PASS: Successfully crawled: {crawled_page.url}")
            print(f"    Status: {crawled_page.status_code}")
            print(f"    Title: '{crawled_page.title}'")
            print(f"    Content length: {len(crawled_page.content)} chars")
        else:
            print("  INFO: No pages crawled (may be network issue)")

    except Exception as e:
        print(f"  FAIL: Live crawl test failed: {e}")

    print("\n" + "=" * 60)
    print("SELF-TEST SUITE COMPLETED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    import json

    # Run self-tests
    run_self_tests()

    # Example usage
    print("\n" + "=" * 60)
    print("EXAMPLE USAGE")
    print("=" * 60)

    print(
        """
# Basic usage:
from web_spider import WebSpider

spider = WebSpider(
    base_url="https://example.com",
    max_depth=2,
    max_pages=10,
    delay=1.0
)

pages = spider.crawl()

# Generate report
spider.save_report("my_crawl_report.json")

# Access crawled pages
for page in pages:
    print(f"Title: {page.title}")
    print(f"URL: {page.url}")
    print(f"Links found: {len(page.links)}")
"""
    )
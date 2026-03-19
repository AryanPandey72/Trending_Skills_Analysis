import asyncio
import httpx
from bs4 import BeautifulSoup
import urllib.parse
import re

class IndeedScraper:
    def __init__(self):
        self.base_url = "https://www.indeed.com/jobs"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def get_jobs(self, job_title: str, max_jobs: int = 50) -> list[dict]:
        """Scrape jobs from Indeed using httpx (no browser needed)."""
        jobs = []
        encoded_title = urllib.parse.quote(job_title)
        search_url = f"{self.base_url}?q={encoded_title}&l="

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=30.0) as client:
            try:
                response = await client.get(search_url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                job_cards = soup.find_all('div', class_=re.compile(r'job_seen_beacon'))

                for card in job_cards[:max_jobs]:
                    try:
                        title_elem = card.find('h2', class_='jobTitle')
                        company_elem = card.find('span', {'data-testid': 'company-name'})
                        location_elem = card.find('div', {'data-testid': 'text-location'})
                        link_elem = title_elem.find('a') if title_elem else None
                        salary_elem = card.find('div', class_='salary-snippet-container')
                        snippet_elem = card.find('div', class_='job-snippet')

                        title = title_elem.text.strip() if title_elem else "Unknown"
                        company = company_elem.text.strip() if company_elem else "Unknown"
                        location = location_elem.text.strip() if location_elem else "Unknown"
                        link = "https://www.indeed.com" + link_elem['href'] if link_elem and 'href' in link_elem.attrs else ""
                        salary = salary_elem.text.strip() if salary_elem else "Not Specified"
                        snippet = snippet_elem.text.strip() if snippet_elem else ""

                        jobs.append({
                            "platform": "Indeed",
                            "title": title,
                            "company": company,
                            "location": location,
                            "salary_raw": salary,
                            "link": link,
                            "description": snippet
                        })
                    except Exception as e:
                        print(f"Error parsing job card: {e}")
                        continue

            except Exception as e:
                print(f"Error scraping Indeed: {e}")

        return jobs

async def test_scraper():
    scraper = IndeedScraper()
    jobs = await scraper.get_jobs("Frontend Developer", max_jobs=5)
    print(f"Scraped {len(jobs)} jobs from Indeed.")
    for j in jobs:
        print(j)

if __name__ == "__main__":
    asyncio.run(test_scraper())

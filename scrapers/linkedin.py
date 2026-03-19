import asyncio
import httpx
from bs4 import BeautifulSoup
import urllib.parse
import re

class LinkedInScraper:
    def __init__(self):
        self.base_url = "https://www.linkedin.com/jobs/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def get_jobs(self, job_title: str, max_jobs: int = 50) -> list[dict]:
        """Scrape jobs from LinkedIn using httpx (no browser needed)."""
        jobs = []
        encoded_title = urllib.parse.quote(job_title)
        search_url = f"{self.base_url}?keywords={encoded_title}&location=United%20States"

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=30.0) as client:
            try:
                response = await client.get(search_url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                job_cards = soup.find_all('div', class_='base-card')
                if not job_cards:
                    job_cards = soup.find_all('li', class_=re.compile(r'job-search-card'))

                for card in job_cards[:max_jobs]:
                    try:
                        title_elem = card.find('h3', class_='base-search-card__title')
                        company_elem = card.find('h4', class_='base-search-card__subtitle')
                        location_elem = card.find('span', class_='job-search-card__location')
                        link_elem = card.find('a', class_='base-card__full-link')

                        title = title_elem.text.strip() if title_elem else "Unknown"
                        company = company_elem.text.strip() if company_elem else "Unknown"
                        location = location_elem.text.strip() if location_elem else "Unknown"
                        link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ""

                        description = f"Extracted from {link}"
                        if link:
                            try:
                                desc_resp = await client.get(link)
                                desc_soup = BeautifulSoup(desc_resp.text, 'html.parser')
                                desc_div = desc_soup.find('div', class_='show-more-less-html__markup')
                                if desc_div:
                                    description = desc_div.text.strip()
                            except Exception as e:
                                print(f"Error fetching description for {link}: {e}")

                        jobs.append({
                            "platform": "LinkedIn",
                            "title": title,
                            "company": company,
                            "location": location,
                            "link": link,
                            "description": description
                        })
                    except Exception as e:
                        print(f"Error parsing job card: {e}")
                        continue

            except Exception as e:
                print(f"Error scraping LinkedIn: {e}")

        return jobs

async def test_scraper():
    scraper = LinkedInScraper()
    jobs = await scraper.get_jobs("Data Scientist", max_jobs=5)
    print(f"Scraped {len(jobs)} jobs from LinkedIn.")
    for j in jobs:
        print(j)

if __name__ == "__main__":
    asyncio.run(test_scraper())

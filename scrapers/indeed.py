import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import urllib.parse
import re

class IndeedScraper:
    def __init__(self):
        self.base_url = "https://www.indeed.com/jobs"

    async def get_jobs(self, job_title: str, max_jobs: int = 50) -> list[dict]:
        """Scrape jobs from Indeed."""
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            encoded_title = urllib.parse.quote(job_title)
            search_url = f"{self.base_url}?q={encoded_title}&l="
            
            try:
                # Indeed aggressively blocks scraping, Cloudflare checks might trigger.
                await page.goto(search_url, wait_until="networkidle", timeout=60000)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
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
                
            finally:
                await browser.close()
                
        return jobs

async def test_scraper():
    scraper = IndeedScraper()
    jobs = await scraper.get_jobs("Frontend Developer", max_jobs=5)
    print(f"Scraped {len(jobs)} jobs from Indeed.")
    for j in jobs:
        print(j)

if __name__ == "__main__":
    asyncio.run(test_scraper())

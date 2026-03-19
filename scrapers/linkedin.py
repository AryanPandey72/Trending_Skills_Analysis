import asyncio
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
import urllib.parse
import re

class LinkedInScraper:
    def __init__(self):
        self.base_url = "https://www.linkedin.com/jobs/search"

    async def get_jobs(self, job_title: str, max_jobs: int = 50) -> list[dict]:
        """Scrape jobs from LinkedIn."""
        jobs = []
        async with async_playwright() as p:
            # Try to launch visible and with a slower, more human profile to avoid blocking.
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            encoded_title = urllib.parse.quote(job_title)
            # Using location=Worldwide or United States as default
            search_url = f"{self.base_url}?keywords={encoded_title}&location=United%20States"
            
            try:
                await page.goto(search_url, wait_until="networkidle", timeout=60000)
                # Scroll down repeatedly to load more jobs (infinite scroll)
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                job_cards = soup.find_all('div', class_='base-card')
                if not job_cards:
                    # Alternative structure sometimes loaded
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
                        
                        description = f"Extracted from {link}" # Fallback
                        if link:
                            try:
                                # Need to fetch the actual description page
                                desc_page = await context.new_page()
                                await desc_page.goto(link, wait_until="domcontentloaded", timeout=15000)
                                # The description on linkedin guest views is usually in a div with this class
                                desc_content = await desc_page.content()
                                desc_soup = BeautifulSoup(desc_content, 'html.parser')
                                
                                desc_div = desc_soup.find('div', class_='show-more-less-html__markup')
                                if desc_div:
                                    description = desc_div.text.strip()
                                    
                                await desc_page.close()
                            except Exception as e:
                                print(f"Error fetching description for {link}: {e}")
                                # Clean up page if it exists
                                try:
                                    await desc_page.close()
                                except:
                                    pass
                        
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
                
            finally:
                await browser.close()
                
        return jobs

async def test_scraper():
    scraper = LinkedInScraper()
    jobs = await scraper.get_jobs("Data Scientist", max_jobs=5)
    print(f"Scraped {len(jobs)} jobs from LinkedIn.")
    for j in jobs:
        print(j)

if __name__ == "__main__":
    asyncio.run(test_scraper())

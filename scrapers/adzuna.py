import httpx
import asyncio
import os
import math

class AdzunaScraper:
    """Fetch job listings from the Adzuna REST API (structured JSON, no browser needed)."""

    COUNTRY_CODES = {
        "India": "in",
        "United States": "us",
        "United Kingdom": "gb",
        "Canada": "ca",
        "Australia": "au",
        "Germany": "de",
        "France": "fr",
        "Singapore": "sg",
    }

    def __init__(self, app_id=None, app_key=None, country="in"):
        self.app_id = app_id or os.environ.get("ADZUNA_APP_ID")
        self.app_key = app_key or os.environ.get("ADZUNA_API_KEY")
        self.country = country
        self.base_url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search"

    async def get_jobs(self, job_title: str, max_jobs: int = 50) -> list[dict]:
        """Fetch jobs from Adzuna API, paginated up to max_jobs."""
        jobs = []
        results_per_page = 50  # Adzuna max per page
        total_pages = math.ceil(max_jobs / results_per_page)

        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in range(1, total_pages + 1):
                params = {
                    "app_id": self.app_id,
                    "app_key": self.app_key,
                    "results_per_page": min(results_per_page, max_jobs - len(jobs)),
                    "what": job_title,
                    "content-type": "application/json",
                }

                try:
                    response = await client.get(f"{self.base_url}/{page}", params=params)
                    response.raise_for_status()
                    data = response.json()

                    results = data.get("results", [])
                    if not results:
                        break

                    for r in results:
                        company_info = r.get("company", {})
                        location_info = r.get("location", {})

                        # Build salary string from min/max if available
                        sal_min = r.get("salary_min")
                        sal_max = r.get("salary_max")
                        if sal_min and sal_max:
                            salary_raw = f"{int(sal_min)} - {int(sal_max)}"
                        elif sal_min:
                            salary_raw = str(int(sal_min))
                        elif sal_max:
                            salary_raw = str(int(sal_max))
                        else:
                            salary_raw = "Not Specified"

                        jobs.append({
                            "platform": "Adzuna",
                            "title": r.get("title", "Unknown"),
                            "company": company_info.get("display_name", "Unknown"),
                            "location": location_info.get("display_name", "Unknown"),
                            "description": r.get("description", ""),
                            "salary_raw": salary_raw,
                            "link": r.get("redirect_url", ""),
                        })

                        if len(jobs) >= max_jobs:
                            break

                except Exception as e:
                    print(f"Error fetching Adzuna page {page}: {e}")
                    break

                if len(jobs) >= max_jobs:
                    break

        return jobs


async def test_scraper():
    from dotenv import load_dotenv
    load_dotenv()
    scraper = AdzunaScraper(country="in")
    jobs = await scraper.get_jobs("Data Scientist", max_jobs=5)
    print(f"Fetched {len(jobs)} jobs from Adzuna.")
    for j in jobs:
        print(f"  {j['title']} @ {j['company']} | {j['location']} | Salary: {j['salary_raw']}")
        print(f"    Desc: {j['description'][:120]}...")
        print()

if __name__ == "__main__":
    asyncio.run(test_scraper())

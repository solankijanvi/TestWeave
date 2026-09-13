from collections import deque
from url_utils import normalize_url,is_same_domain
from page_analyzer import analyze_page

async def crawl_application(page, start_url: str, max_pages: int = 10):
    visited = set()
    queue = deque([start_url])
    pages = []
    
    
    while queue and len(visited) < max_pages:
        current_url =queue.popleft()
        if current_url in visited:
            continue
        
        visited.add(current_url)
        
        print(f"Crawling: {current_url}")

        try:
            await page.goto(
                current_url,
                wait_until="domcontentloaded",
                timeout=30000
            )
             # Give a deployed application time to finish loading
            await page.wait_for_timeout(5000)

            page_data = await analyze_page(page)

            
            # Ignore hosting-provider loading pages
            if "Application loading" in page_data["title"]:
                print("Application is still starting. Waiting...")
                await page.wait_for_timeout(10000)

                await page.reload(
                    wait_until="domcontentloaded",
                    timeout=30000
                )
            pages.append(page_data)
            
            for link in page_data["links"]:
                next_url = normalize_url(current_url, link["href"])
                
                
                
                if (
                    next_url
                    and is_same_domain(start_url, next_url)
                    and next_url not in visited
                ):
                    
                    queue.append(next_url)   
                
        except Exception as error:
            print(f"Failed to crawl {current_url}: {error}")

    return pages
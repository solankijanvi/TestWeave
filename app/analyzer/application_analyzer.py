def analyze_application(application):
    analysis = {
        "start_url": application.start_url,
        "total_pages": application.total_pages,
        "pages": []
    }
    
    for page in application.pages:
        page_analysis = {
            "url": page.url,
            "title": page.title,
            "headings": page.headings,
            "inputs": page.inputs,
            "buttons": page.buttons,
            "forms": page.forms,
            "links": page.links
            
        }
        
        analysis["pages"].append(page_analysis)
        
    return analysis
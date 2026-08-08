import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import time
import json
import os

sitemap_url = "https://www.nitrkl.ac.in/sitemap.xml"
doc_extensions = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx')
sleep_time = 1
timeout = 10
save_every = 25
download_dir = "downloads"
download_timeout = 20
download_sleep = 0.5

os.makedirs(download_dir, exist_ok=True)


def get_sitemap_urls(sitemap_url):
    resp = requests.get(sitemap_url, timeout=timeout)
    soup = BeautifulSoup(resp.content, 'xml')
    urls = [loc.text.strip() for loc in soup.find_all('loc')]
    return urls


def scrape_page(url):
    resp = requests.get(url, timeout=timeout)
    if resp.status_code != 200:
        return False, f"status code {resp.status_code}"

    soup = BeautifulSoup(resp.text, 'html.parser')

    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()

    page_text = soup.get_text(separator=' ', strip=True)

    doc_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().endswith(doc_extensions):
            full_url = urljoin(url, href)
            doc_links.append(full_url)

    return True, {
        "url": url,
        "text": page_text,
        "doc_links": doc_links
    }


def save_scrape_progress(results, failed):
    with open('scraped_pages.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open('failed_urls.json', 'w', encoding='utf-8') as f:
        json.dump(failed, f, indent=2, ensure_ascii=False)


def scrape_site():
    print("fetching sitemap...")
    urls = get_sitemap_urls(sitemap_url)
    urls = list(dict.fromkeys(urls))
    print(f"total unique urls: {len(urls)}")

    results = []
    failed = []

    for i, url in enumerate(urls):
        try:
            success, data = scrape_page(url)
            if success:
                results.append(data)
            else:
                failed.append({"url": url, "reason": data})
        except Exception as e:
            failed.append({"url": url, "reason": str(e)})

        if i % 20 == 0:
            print(f"progress: {i}/{len(urls)} (success={len(results)}, failed={len(failed)})")

        if i % save_every == 0 and i > 0:
            save_scrape_progress(results, failed)

        time.sleep(sleep_time)

    save_scrape_progress(results, failed)

    all_docs = set()
    for item in results:
        for link in item['doc_links']:
            all_docs.add(link)

    with open('all_documents.json', 'w', encoding='utf-8') as f:
        json.dump(sorted(all_docs), f, indent=2)

    print(f"scrape done. pages success: {len(results)}, failed: {len(failed)}")
    print(f"unique documents found: {len(all_docs)}")

    return sorted(all_docs)


def is_nitrkl_domain(url):
    domain = urlparse(url).netloc.lower()
    return domain.endswith("nitrkl.ac.in")


def safe_filename(url, index):
    path = urlparse(url).path
    name = unquote(os.path.basename(path))
    name = name.strip() or f"file_{index}"
    for ch in ['?', '*', ':', '"', '<', '>', '|']:
        name = name.replace(ch, '_')
    return f"{index:04d}_{name}"


def download_documents(all_docs):
    print(f"total docs found: {len(all_docs)}")

    nitrkl_docs = [u for u in all_docs if is_nitrkl_domain(u)]
    external_docs = [u for u in all_docs if not is_nitrkl_domain(u)]

    print(f"nitrkl domain docs: {len(nitrkl_docs)}")
    print(f"external docs skipped: {len(external_docs)}")

    with open('skipped_external_docs.json', 'w', encoding='utf-8') as f:
        json.dump(external_docs, f, indent=2)

    manifest = []
    failed = []

    for i, url in enumerate(nitrkl_docs):
        filename = safe_filename(url, i)
        filepath = os.path.join(download_dir, filename)

        if os.path.exists(filepath):
            manifest.append({"url": url, "file": filename, "status": "already_exists"})
            continue

        try:
            resp = requests.get(url, timeout=download_timeout, stream=True)
            if resp.status_code != 200:
                failed.append({"url": url, "reason": f"status {resp.status_code}"})
                continue

            content_type = resp.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                failed.append({"url": url, "reason": f"got html instead of file ({content_type})"})
                continue

            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            size = os.path.getsize(filepath)
            manifest.append({"url": url, "file": filename, "status": "downloaded", "size_bytes": size})

        except Exception as e:
            failed.append({"url": url, "reason": str(e)})

        if i % 20 == 0:
            print(f"progress: {i}/{len(nitrkl_docs)} (ok={len(manifest)}, failed={len(failed)})")
            with open('download_manifest.json', 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            with open('download_failed.json', 'w', encoding='utf-8') as f:
                json.dump(failed, f, indent=2)

        time.sleep(download_sleep)

    with open('download_manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    with open('download_failed.json', 'w', encoding='utf-8') as f:
        json.dump(failed, f, indent=2)

    print(f"download done. downloaded/existing: {len(manifest)}, failed: {len(failed)}")
    print("files saved in:", download_dir)


if __name__ == "__main__":
    docs = scrape_site()
    download_documents(docs)
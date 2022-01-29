import asyncio
import itertools
import aiohttp
import aiofiles
import os
import re
import json


URL_PATTERN = re.compile(r'"/[^"]+"')
session = None


def flatten(obj):
    while isinstance(obj[0], (list, tuple)):
        obj = list(itertools.chain.from_iterable(obj))
    return obj


def print_prefix(page, content):
    if not isinstance(page, int):
        c = hash(page) % 14
    else:
        c = page % 14
    if c >= 7:
        c += 53
    c += 31
    print(f"\033[{c}m{page}: {content}\033[m")


async def download(url):
    async with session.get(f"https://servers.purplepalette.net/{url}") as response:
        print_prefix(url, "Writing to file...")
        os.makedirs(os.path.dirname(f"./result{url}"), exist_ok=True)
        async with aiofiles.open(f"./result{url}", "wb") as f:
            while True:
                try:
                    d = await response.read()
                    await asyncio.sleep(0)
                    await f.write(d)
                    break
                except aiohttp.client_exceptions.ClientPayloadError:
                    print_prefix(url, "Retrying...")
                    pass  # Retry


async def crawl_level(name):
    print_prefix(name, f"Querying /level/{name}")
    async with session.get(f"https://servers.purplepalette.net/levels/{name}") as response:
        if not os.path.exists(f"./result/levels/{name}.json"):
            print_prefix(name, "Writing to file...")
            async with aiofiles.open(f"./result/levels/{name}.json", "w") as f:
                await f.write(await response.text())
        data = await response.text()
    urls = []
    print_prefix(name, "Finding URL...")
    for url in URL_PATTERN.finditer(data):
        urls.append(url.group(0)[1:-1])
    return urls


async def crawl_page(page):
    print_prefix(page, f"Querying /list?page={page}")
    async with session.get("https://servers.purplepalette.net/levels/list", params={"page": page}) as response:
        if not os.path.exists(f"./result/list/{page}.json"):
            async with aiofiles.open(f"./result/list/{page}.json", "w") as f:
                print_prefix(page, "Writing to file...")
                data = await response.json()
                del data["search"]
                await f.write(json.dumps(data))
        data = await response.json()
    coros = []
    for level in data["items"]:
        coros.append(crawl_level(level["name"]))
    return await asyncio.gather(*coros)


async def main():
    global session
    session = aiohttp.ClientSession()
    os.makedirs("./result/repository", exist_ok=True)
    os.makedirs("./result/list", exist_ok=True)
    os.makedirs("./result/levels", exist_ok=True)
    coros = []
    async with session.get("https://servers.purplepalette.net/levels/list") as response:
        res = await response.json()
        for page in range(1, int(res["pageCount"]) + 1):
            coros.append(crawl_page(page))
    urls = await asyncio.gather(*coros)
    coros = []
    for url in set(flatten(urls)):
        coros.append(download(url))
    await asyncio.gather(*coros)


if __name__ == "__main__":
    os.system("")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

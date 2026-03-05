"""
Scrapes celebrity lists from Wikipedia (Twitter/Instagram/TikTok/Facebook)
and queries justice.gov/multimedia-search for Epstein document mention counts.
Also builds rich descriptions from Wikipedia full-article text (including
controversy/scandal/criticism sections).

Usage:
    python scrape_celebrities.py            # full pipeline -> celebrities.json
    python scrape_celebrities.py --doj      # only DOJ counts
    python scrape_celebrities.py --wiki     # only Wikipedia data
"""

import urllib.request
import urllib.error
import urllib.parse
import gzip
import re
import json
import time
import sys

# -- Session cookies copied from browser ---------------------------------------
DOJ_COOKIES = (
    'QueueITAccepted-SDFrts345E-V3_usdojsearch=EventId%3Dusdojsearch%26RedirectType%3Dsafetynet'
    '%26IssueTime%3D1772678207%26Hash%3D9fb4f851a1363f2d0a89844b3174684bc382a21dba8e09ff5e15b76e8b04e361; '
    'ak_bmsc=930694C2FDF357268134C8FF0F8BEFD0~000000000000000000000000000000~YAAQ6qXcF530x6ScAQAAd9naux'
    '+iqZOTnFVifakii5I5WCgsgvJZfhqfpuY4DcpeB52LzSXP3NxMyIbMZp8B8b/rLw/oj3q/hchVdXxv1FBmYpfm2NWg26HUYuw6d5ia6s'
    'xUs0MiRiqmSVAsnrwGrbM2d02nRqTmpJBRqiSvBHpa4LNO8Q8BVSzrdHmY1yfsZ6DsbC149xsH7cqO766CWXVRUcli0AwdM/VfC5qVCSC'
    'J9uWN1ofj2nYTcgCfOfQIkM9Jce/IPfa2w6feODXxEK2EO5QKQu2sDPOE3638FH2lUOhigwKEsKZHJWlM3LykZKfZM1DcoX+I5pUDjkV'
    'FeVHR82DWCQVEP4Z9cUI39YA3FJXsckWCMVQUnuUScLM5fxT143lOQKxo1tr9Bu72A4AEwxH9vcM6EGIMA/MJZHiPMuDxYtTMDd7F0+hs'
    '9YfM9S7ga2nT9/3lgtLUfmrQiwptrfd8lyg=; '
    '_ga=GA1.1.1652750234.1772678210; '
    'justiceGovAgeVerified=true; '
    '_ga_CSLL4ZEK4L=GS2.1.s1772678209$o1$g1$t1772678239$j30$l0$h0'
)

DOJ_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'cookie': DOJ_COOKIES,
    'priority': 'u=1, i',
    'referer': 'https://www.justice.gov/epstein',
    'sec-ch-ua': '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"iOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': (
        'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) '
        'AppleWebKit/605.1.15 (KHTML, like Gecko) '
        'Version/18.5 Mobile/15E148 Safari/604.1 Edg/145.0.0.0'
    ),
    'x-queueit-ajaxpageurl': 'https%3A%2F%2Fwww.justice.gov%2Fepstein',
}

WIKI_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Referer': 'https://www.google.com/',
}

WIKI_API_HEADERS = {
    'User-Agent': 'EpsteinGame/1.0 (educational project)',
    'Accept': 'application/json',
}

# -- Celebrity list ------------------------------------------------------------
# (full_name, doj_search_term, wikipedia_slug)
CELEBRITIES = [
    # Businesspeople / Politicians
    ("Bill Gates",            "Bill Gates",        "Bill_Gates"),
    ("Elon Musk",             "Elon Musk",         "Elon_Musk"),
    ("Barack Obama",          "Barack Obama",      "Barack_Obama"),
    ("Donald Trump",          "Donald Trump",      "Donald_Trump"),
    ("Joe Biden",             "Joe Biden",         "Joe_Biden"),
    ("Justin Trudeau",        "Trudeau",           "Justin_Trudeau"),
    ("Narendra Modi",         "Modi",              "Narendra_Modi"),
    ("Richard Branson",       "Richard Branson",   "Richard_Branson"),
    ("Mark Cuban",            "Mark Cuban",        "Mark_Cuban"),
    ("Jeff Bezos",            "Jeff Bezos",        "Jeff_Bezos"),
    ("Warren Buffett",        "Buffett",           "Warren_Buffett"),
    ("Rupert Murdoch",        "Rupert Murdoch",    "Rupert_Murdoch"),
    # TV / Media
    ("Oprah Winfrey",         "Oprah",             "Oprah_Winfrey"),
    ("Ellen DeGeneres",       "DeGeneres",         "Ellen_DeGeneres"),
    ("Jimmy Fallon",          "Jimmy Fallon",      "Jimmy_Fallon"),
    # Musicians
    ("Beyonce",               "Beyonce",           "Beyonce"),
    ("Taylor Swift",          "Taylor Swift",      "Taylor_Swift"),
    ("Rihanna",               "Rihanna",           "Rihanna"),
    ("Justin Bieber",         "Justin Bieber",     "Justin_Bieber"),
    ("Katy Perry",            "Katy Perry",        "Katy_Perry"),
    ("Lady Gaga",             "Lady Gaga",         "Lady_Gaga"),
    ("Ariana Grande",         "Ariana Grande",     "Ariana_Grande"),
    ("Selena Gomez",          "Selena Gomez",      "Selena_Gomez"),
    ("Miley Cyrus",           "Miley Cyrus",       "Miley_Cyrus"),
    ("Demi Lovato",           "Demi Lovato",       "Demi_Lovato"),
    ("Britney Spears",        "Britney Spears",    "Britney_Spears"),
    ("Shakira",               "Shakira",           "Shakira"),
    ("Drake",                 "Drake",             "Drake_(musician)"),
    ("Chris Brown",           "Chris Brown",       "Chris_Brown"),
    ("Billie Eilish",         "Billie Eilish",     "Billie_Eilish"),
    ("Dua Lipa",              "Dua Lipa",          "Dua_Lipa"),
    ("Snoop Dogg",            "Snoop Dogg",        "Snoop_Dogg"),
    ("Justin Timberlake",     "Justin Timberlake", "Justin_Timberlake"),
    ("Eminem",                "Eminem",            "Eminem"),
    ("Michael Jackson",       "Michael Jackson",   "Michael_Jackson"),
    ("Adele",                 "Adele",             "Adele"),
    ("Bruno Mars",            "Bruno Mars",        "Bruno_Mars"),
    ("Jason Derulo",          "Jason Derulo",      "Jason_Derulo"),
    ("Will Smith",            "Will Smith",        "Will_Smith_(actor)"),
    # Reality / Social Media
    ("Kim Kardashian",        "Kim Kardashian",    "Kim_Kardashian"),
    ("Kylie Jenner",          "Kylie Jenner",      "Kylie_Jenner"),
    ("Khloe Kardashian",      "Khloe Kardashian",  "Khloe_Kardashian"),
    ("Kendall Jenner",        "Kendall Jenner",    "Kendall_Jenner"),
    ("Charli D'Amelio",       "Charli D'Amelio",   "Charli_D%27Amelio"),
    ("Addison Rae",           "Addison Rae",       "Addison_Rae"),
    ("Bella Poarch",          "Bella Poarch",      "Bella_Poarch"),
    ("Khaby Lame",            "Khaby Lame",        "Khaby_Lame"),
    ("JoJo Siwa",             "JoJo Siwa",         "JoJo_Siwa"),
    # Actors
    ("Dwayne Johnson",        "Dwayne Johnson",    "Dwayne_Johnson"),
    ("Kevin Hart",            "Kevin Hart",        "Kevin_Hart_(actor)"),
    ("Vin Diesel",            "Vin Diesel",        "Vin_Diesel"),
    ("Gal Gadot",             "Gal Gadot",         "Gal_Gadot"),
    ("Zendaya",               "Zendaya",           "Zendaya"),
    ("Jennifer Lopez",        "Jennifer Lopez",    "Jennifer_Lopez"),
    ("Jackie Chan",           "Jackie Chan",       "Jackie_Chan"),
    ("Jason Statham",         "Jason Statham",     "Jason_Statham"),
    # Sports
    ("LeBron James",          "LeBron James",      "LeBron_James"),
    ("Cristiano Ronaldo",     "Cristiano Ronaldo", "Cristiano_Ronaldo"),
    ("Lionel Messi",          "Lionel Messi",      "Lionel_Messi"),
    ("Neymar",                "Neymar",            "Neymar"),
    ("David Beckham",         "David Beckham",     "David_Beckham"),
    ("Cardi B",               "Cardi B",           "Cardi_B"),
    # Business / Motivational
    ("Tony Robbins",          "Tony Robbins",      "Tony_Robbins"),
    ("Gary Vaynerchuk",       "Gary Vaynerchuk",   "Gary_Vaynerchuk"),
    # Spotify — most-streamed artists
    ("Ed Sheeran",            "Ed Sheeran",        "Ed_Sheeran"),
    ("The Weeknd",            "The Weeknd",        "The_Weeknd"),
    ("Bad Bunny",             "Bad Bunny",         "Bad_Bunny"),
    ("Post Malone",           "Post Malone",       "Post_Malone"),
    ("Juice WRLD",            "Juice WRLD",        "Juice_Wrld"),
    ("J Balvin",              "J Balvin",          "J_Balvin"),
    ("Daddy Yankee",          "Daddy Yankee",      "Daddy_Yankee"),
    ("Nicki Minaj",           "Nicki Minaj",       "Nicki_Minaj"),
    ("Kanye West",            "Kanye West",        "Kanye_West"),
    ("Jay-Z",                 "Jay-Z",             "Jay-Z"),
    ("Kendrick Lamar",        "Kendrick Lamar",    "Kendrick_Lamar"),
    ("Travis Scott",          "Travis Scott",      "Travis_Scott_(rapper)"),
    ("Calvin Harris",         "Calvin Harris",     "Calvin_Harris"),
    ("Marshmello",            "Marshmello",        "Marshmello"),
    ("Harry Styles",          "Harry Styles",      "Harry_Styles"),
    ("Olivia Rodrigo",        "Olivia Rodrigo",    "Olivia_Rodrigo"),
    ("Doja Cat",              "Doja Cat",          "Doja_Cat"),
    ("Sam Smith",             "Sam Smith",         "Sam_Smith_(singer)"),
    ("Shawn Mendes",          "Shawn Mendes",      "Shawn_Mendes"),
    ("Lil Wayne",             "Lil Wayne",         "Lil_Wayne"),
    ("XXXTentacion",          "XXXTentacion",      "XXXTentacion"),
    ("Camila Cabello",        "Camila Cabello",    "Camila_Cabello"),
    ("Lizzo",                 "Lizzo",             "Lizzo"),
    ("SZA",                   "SZA",               "SZA_(singer)"),
    ("Maluma",                "Maluma",            "Maluma_(singer)"),
    ("Ozuna",                 "Ozuna",             "Ozuna_(singer)"),
    # Academy Award — Best Actor (selected winners)
    ("Tom Hanks",             "Tom Hanks",         "Tom_Hanks"),
    ("Leonardo DiCaprio",     "Leonardo DiCaprio", "Leonardo_DiCaprio"),
    ("Denzel Washington",     "Denzel Washington", "Denzel_Washington"),
    ("Joaquin Phoenix",       "Joaquin Phoenix",   "Joaquin_Phoenix"),
    ("Anthony Hopkins",       "Anthony Hopkins",   "Anthony_Hopkins"),
    ("Russell Crowe",         "Russell Crowe",     "Russell_Crowe"),
    ("Matthew McConaughey",   "McConaughey",       "Matthew_McConaughey"),
    ("Jamie Foxx",            "Jamie Foxx",        "Jamie_Foxx"),
    ("Adrien Brody",          "Adrien Brody",      "Adrien_Brody"),
    ("Colin Firth",           "Colin Firth",       "Colin_Firth"),
    ("Jack Nicholson",        "Jack Nicholson",    "Jack_Nicholson"),
    ("Al Pacino",             "Al Pacino",         "Al_Pacino"),
    ("Robert De Niro",        "Robert De Niro",    "Robert_De_Niro"),
    ("Morgan Freeman",        "Morgan Freeman",    "Morgan_Freeman"),
    ("Brad Pitt",             "Brad Pitt",         "Brad_Pitt"),
    ("Johnny Depp",           "Johnny Depp",       "Johnny_Depp"),
    ("George Clooney",        "George Clooney",    "George_Clooney"),
    ("Matt Damon",            "Matt Damon",        "Matt_Damon"),
    ("Ben Affleck",           "Ben Affleck",       "Ben_Affleck"),
    ("Sylvester Stallone",    "Sylvester Stallone","Sylvester_Stallone"),
    ("Arnold Schwarzenegger", "Schwarzenegger",    "Arnold_Schwarzenegger"),
    ("Harrison Ford",         "Harrison Ford",     "Harrison_Ford_(actor)"),
    ("Sean Penn",             "Sean Penn",         "Sean_Penn"),
    ("Daniel Day-Lewis",      "Daniel Day-Lewis",  "Daniel_Day-Lewis"),
    ("Jeff Bridges",          "Jeff Bridges",      "Jeff_Bridges"),
    ("Forest Whitaker",       "Forest Whitaker",   "Forest_Whitaker"),
    ("Philip Seymour Hoffman","Philip Seymour Hoffman","Philip_Seymour_Hoffman"),
    # US Representatives (notable current & recent)
    ("Nancy Pelosi",          "Nancy Pelosi",      "Nancy_Pelosi"),
    ("Alexandria Ocasio-Cortez","Alexandria Ocasio-Cortez","Alexandria_Ocasio-Cortez"),
    ("Marjorie Taylor Greene","Marjorie Taylor Greene","Marjorie_Taylor_Greene"),
    ("Matt Gaetz",            "Matt Gaetz",        "Matt_Gaetz"),
    ("Jim Jordan",            "Jim Jordan",        "Jim_Jordan_(Ohio_politician)"),
    ("Adam Schiff",           "Adam Schiff",       "Adam_Schiff"),
    ("Ilhan Omar",            "Ilhan Omar",        "Ilhan_Omar"),
    ("Rashida Tlaib",         "Rashida Tlaib",     "Rashida_Tlaib"),
    ("Lauren Boebert",        "Lauren Boebert",    "Lauren_Boebert"),
    ("Maxine Waters",         "Maxine Waters",     "Maxine_Waters"),
    ("Hakeem Jeffries",       "Hakeem Jeffries",   "Hakeem_Jeffries"),
    ("Liz Cheney",            "Liz Cheney",        "Liz_Cheney"),
    ("Paul Ryan",             "Paul Ryan",         "Paul_Ryan"),
    ("Mike Johnson",          "Mike Johnson",      "Mike_Johnson_(Louisiana_politician)"),
    ("George Santos",         "George Santos",     "George_Santos_(politician)"),
    ("Ro Khanna",             "Ro Khanna",         "Ro_Khanna"),
    ("Ted Cruz",              "Ted Cruz",          "Ted_Cruz"),
    ("Marco Rubio",           "Marco Rubio",       "Marco_Rubio"),
    ("Rand Paul",             "Rand Paul",         "Rand_Paul"),
    # Heads of State / Government
    ("Emmanuel Macron",       "Emmanuel Macron",   "Emmanuel_Macron"),
    ("Rishi Sunak",           "Rishi Sunak",       "Rishi_Sunak"),
    ("Olaf Scholz",           "Olaf Scholz",       "Olaf_Scholz"),
    ("Xi Jinping",            "Xi Jinping",        "Xi_Jinping"),
    ("Vladimir Putin",        "Vladimir Putin",    "Vladimir_Putin"),
    ("Kim Jong-un",           "Kim Jong-un",       "Kim_Jong-un"),
    ("Mohammed bin Salman",   "Mohammed bin Salman","Mohammed_bin_Salman"),
    ("Benjamin Netanyahu",    "Netanyahu",         "Benjamin_Netanyahu"),
    ("Volodymyr Zelensky",    "Zelensky",          "Volodymyr_Zelensky"),
    ("Pope Francis",          "Pope Francis",      "Pope_Francis"),
    ("King Charles III",      "King Charles",      "Charles_III"),
    ("Giorgia Meloni",        "Giorgia Meloni",    "Giorgia_Meloni"),
    ("Recep Tayyip Erdogan",  "Erdogan",           "Recep_Tayyip_Erdoğan"),
    ("Jair Bolsonaro",        "Bolsonaro",         "Jair_Bolsonaro"),
    ("Jacinda Ardern",        "Jacinda Ardern",    "Jacinda_Ardern"),
    ("Anthony Albanese",      "Anthony Albanese",  "Anthony_Albanese"),
    ("Lula da Silva",         "Lula",              "Luiz_Inácio_Lula_da_Silva"),
    ("Tony Blair",            "Tony Blair",        "Tony_Blair"),
    ("Gordon Brown",          "Gordon Brown",      "Gordon_Brown"),
    ("Nicolas Sarkozy",       "Nicolas Sarkozy",   "Nicolas_Sarkozy"),
    ("Silvio Berlusconi",     "Silvio Berlusconi", "Silvio_Berlusconi"),
    ("Viktor Orban",          "Viktor Orban",      "Viktor_Orbán"),
    ("Dmitry Medvedev",       "Medvedev",          "Dmitry_Medvedev"),
]

# Section headings to scrape for controversy content
CONTROVERSY_KEYWORDS = {
    'controversy', 'controversies', 'criticism', 'legal issues', 'legal',
    'scandal', 'allegations', 'sexual misconduct', 'arrest', 'criminal',
    'lawsuit', 'public image', 'public perception', 'misconduct',
    'abuse', 'assault', 'incident', 'incidents',
}


# -- Generic fetch -------------------------------------------------------------

def fetch(url: str, headers: dict) -> str:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
        enc = response.info().get('Content-Encoding', '')
        if 'gzip' in enc:
            raw = gzip.decompress(raw)
        return raw.decode('utf-8', errors='replace')


# -- DOJ multimedia-search -----------------------------------------------------

def doj_search_count(query: str) -> int:
    url = (
        'https://www.justice.gov/multimedia-search'
        f'?keys={urllib.parse.quote(query)}&page=0'
    )
    raw = fetch(url, DOJ_HEADERS)
    data = json.loads(raw)
    return data['hits']['total']['value']


# -- Wikipedia -----------------------------------------------------------------

def _clean_html(html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = (text.replace('&nbsp;', ' ').replace('&amp;', '&')
                .replace('&#160;', ' ').replace('&lt;', '<').replace('&gt;', '>'))
    return re.sub(r'\s+', ' ', text).strip()


def get_wikipedia_data(slug: str) -> dict:
    """
    Returns:
        short_desc  - one-line description (Wikipedia short desc)
        intro       - multi-paragraph plain-text intro from REST API
        controversy - text from controversy/legal/scandal sections
        image_url   - thumbnail URL
        wikipedia_url
    """
    result = {
        'short_desc': '',
        'intro': '',
        'controversy': '',
        'image_url': '',
        'wikipedia_url': f'https://en.wikipedia.org/wiki/{slug}',
    }

    # REST summary
    try:
        api_url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(slug)}'
        raw = fetch(api_url, WIKI_API_HEADERS)
        data = json.loads(raw)
        result['short_desc'] = data.get('description', '')
        result['intro'] = data.get('extract', '')
        result['image_url'] = (data.get('thumbnail') or {}).get('source', '')
        result['wikipedia_url'] = (
            data.get('content_urls', {}).get('desktop', {}).get('page', result['wikipedia_url'])
        )
    except Exception as e:
        print(f"    REST error for {slug}: {e}")
        return result

    # Full article for controversy sections
    try:
        html = fetch(f'https://en.wikipedia.org/wiki/{urllib.parse.quote(slug)}', WIKI_HEADERS)

        section_re = re.compile(
            r'<h[23][^>]*>.*?<span[^>]*class="[^"]*mw-headline[^"]*"[^>]*>(.*?)</span>.*?</h[23]>'
            r'(.*?)(?=<h[23]|$)',
            re.DOTALL | re.IGNORECASE,
        )
        parts = []
        for m in section_re.finditer(html):
            heading = _clean_html(m.group(1)).lower()
            if any(kw in heading for kw in CONTROVERSY_KEYWORDS):
                body = _clean_html(m.group(2))[:500]
                if body:
                    parts.append(body)
                if len(parts) >= 2:
                    break

        result['controversy'] = '  '.join(parts)
    except Exception as e:
        print(f"    Full-page error for {slug}: {e}")

    return result


def build_description(data: dict, max_chars: int = 500) -> str:
    """Combine intro + controversy into a rich, readable description."""
    parts = []
    if data.get('intro'):
        parts.append(data['intro'].strip())
    if data.get('controversy'):
        parts.append(data['controversy'].strip())

    combined = '  '.join(parts)

    if len(combined) <= max_chars:
        return combined

    truncated = combined[:max_chars]
    last = max(truncated.rfind('. '), truncated.rfind('! '), truncated.rfind('? '))
    if last > max_chars // 2:
        return truncated[:last + 1]
    return truncated.rstrip() + '...'


# -- Main pipeline -------------------------------------------------------------

def run_doj_counts():
    print('=' * 60)
    print('DOJ EPSTEIN DOCUMENT MENTION COUNTS')
    print('=' * 60)
    results = []
    for full_name, query, slug in CELEBRITIES:
        try:
            count = doj_search_count(query)
            print(f'  {full_name:30s}: {count:6d}')
            results.append((full_name, query, slug, count))
        except Exception as e:
            print(f'  {full_name:30s}: ERROR — {e}')
            results.append((full_name, query, slug, -1))
        time.sleep(0.4)
    return results


def run_wiki_data():
    print('=' * 60)
    print('WIKIPEDIA DATA (with controversy sections)')
    print('=' * 60)
    results = []
    for full_name, query, slug in CELEBRITIES:
        try:
            data = get_wikipedia_data(slug)
            desc = build_description(data, max_chars=500)
            snippet = desc[:90].replace('\n', ' ')
            controversy_flag = 'CONTROVERSY' if data.get('controversy') else ''
            print(f'  {full_name}: {snippet}... {controversy_flag}')
            results.append((full_name, slug, data, desc))
        except Exception as e:
            print(f'  {full_name}: ERROR — {e}')
            results.append((full_name, slug, {}, ''))
        time.sleep(0.3)
    return results


def run_full_pipeline():
    doj_results = run_doj_counts()
    print()
    wiki_results = run_wiki_data()

    wiki_map = {name: (data, desc) for name, slug, data, desc in wiki_results}
    fixture = []
    for full_name, query, slug, count in doj_results:
        wiki_data, desc = wiki_map.get(full_name, ({}, ''))
        fixture.append({
            'full_name': full_name,
            'doj_query': query,
            'wikipedia_slug': slug,
            'epstein_mentions': count,
            'description': desc,
            'extract': (wiki_data or {}).get('intro', ''),
            'image_url': (wiki_data or {}).get('image_url', ''),
            'wikipedia_url': (wiki_data or {}).get('wikipedia_url', ''),
        })

    out_path = 'celebrities.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(fixture, f, indent=2, ensure_ascii=False)
    print(f'\nWrote {len(fixture)} celebrities to {out_path}')
    return fixture


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else '--full'
    if mode == '--doj':
        run_doj_counts()
    elif mode == '--wiki':
        run_wiki_data()
    else:
        run_full_pipeline()

gnore the previous code, I tried to highlight the key differences below: Implement these, increase the build number by 0.1.

class LetterboxdClient:
    def __init__(self, username):
        self.username = username.lstrip('@').strip()

    def fetch_watchlist(self):
        from html import unescape
        movies = []
        page = 1

        while True:
            url = f"https://letterboxd.com/{self.username}/watchlist/page/{page}/"
            #print(f"[Letterboxd] Fetching page {page}: {url}")

            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    html = r.read().decode('utf-8', errors='replace')
                #print(f"[Letterboxd] Got response, length={len(html)} chars")
            except urllib.error.HTTPError as e:
                #print(f"[Letterboxd] HTTPError {e.code} on page {page} — stopping pagination")
                if e.code == 404:
                    break
                raise

            # Dump a snippet so we can see what the page actually looks like
            #print(f"[Letterboxd] HTML snippet (chars 5000-6000):\n{html[5000:6000]}")

            # Find where the film grid actually is
            # if 'poster-container' in html:
            #     idx = html.index('poster-container')
            #     #print(f"[Letterboxd] 'poster-container' found at char {idx}")
            #     #print(f"[Letterboxd] Context around it:\n{html[idx-200:idx+500]}")
            # elif 'film-poster' in html:
            #     idx = html.index('film-poster')
            #     #print(f"[Letterboxd] 'film-poster' found at char {idx}")
            #     #print(f"[Letterboxd] Context around it:\n{html[idx-200:idx+500]}")
            # else:
            #     #print(f"[Letterboxd] Neither 'poster-container' nor 'film-poster' found in HTML!")
            #     #print(f"[Letterboxd] Dumping first 3000 chars to check for bot block / redirect:\n{html[:3000]}")

            poster_divs = re.findall(
                r'<div[^>]+class="react-component"[^>]+data-target-link="/film/[^>]+>',
                html
            )
            #print(f"[Letterboxd] Found {len(poster_divs)} react-component film divs on page {page}")
            #print(f"[Letterboxd] Found {len(poster_divs)} poster-container lis on page {page}")
            #print(f"[Letterboxd] Found {len(poster_divs)} film-poster divs on page {page}")

            if not poster_divs:
                #print(f"[Letterboxd] No films found on page {page} — stopping")
                break

            for i, tag in enumerate(poster_divs):
                #print(f"[Letterboxd]   [{i}] Raw tag: {tag[:200]}")  # truncate — these tags are long

                # slug is like /film/mississippi-masala/
                slug_m = re.search(r'data-target-link="/film/([^/]+)/"', tag)
                
                # title comes from the alt text on the <img> — but that's outside this tag.
                # Instead, convert the slug to a title as a fallback
                slug = slug_m.group(1) if slug_m else None
                if not slug:
                    #print(f"[Letterboxd]   [{i}] No slug found — skipping")
                    continue

                # Convert slug to a readable title: "mississippi-masala" -> "Mississippi Masala"
                title = slug.replace('-', ' ').title()
                #print(f"[Letterboxd]   [{i}] slug={slug!r}  title={title!r}")

                # Year isn't in this tag — TMDB lookup will get it
                movies.append({
                    'title':        title,
                    'year':         0,
                    'genre':        'Unknown',
                    'country':      '?',
                    'rating':       0.0,
                    'lb_added':     '',
                    'poster_url':   None,
                    'poster_color': CARD,
                    'runtime':      0,
                    'director':     'Unknown',
                    'source':       'letterboxd',
                })
            # Check for next page
            next_page_url = f'/watchlist/page/{page + 1}/'
            has_next = next_page_url in html
            #print(f"[Letterboxd] Next page check: {next_page_url!r} in html → {has_next}")

            if not has_next:
                #print(f"[Letterboxd] No next page found — done after page {page}")
                break

            page += 1

        #print(f"[Letterboxd] Done. Total films fetched: {len(movies)}")
        return movies


def fetch_plex_async(url, token, on_done, on_error):
    def run():
        try:
            movies = PlexClient(url, token).fetch_movies()
            Clock.schedule_once(lambda dt: on_done(movies), 0)
        except Exception as e:
            exc = e
            Clock.schedule_once(lambda dt: on_error(str(exc)), 0)
    threading.Thread(target=run, daemon=True).start()

def fetch_lb_async(username, on_done, on_error):
    def run():
        try:
            movies = LetterboxdClient(username).fetch_watchlist()
            Clock.schedule_once(lambda dt: on_done(movies), 0)
        except Exception as e:
            exc =  e
            #print(f"Letterboxd error - {e}")
            Clock.schedule_once(lambda dt: on_error(str(exc)), 0)
    threading.Thread(target=run, daemon=True).start()

Build these changes.

Now for some new stuff. This is also going to be a new build so up the version number by 0.1 again.


Going forward, include similar debug statements for me to use in the app, both on the pc and phone. Some features I want developed
-preload all the poster and movie info, hide this behind a short loading screen
-find the intersection between the movies sourced from plex and those from letterboxd
-highlight when something belongs to one or both
-there's some broken data for some of the movies. Use moviedmb as a second source of truth to fill in the gaps and avoid this, Dont display anything that looks wrong (bad formatting, multiple unknown fields, 0 min runtime etc)
-fetch some analytics from letterboxd (watched this year etc)

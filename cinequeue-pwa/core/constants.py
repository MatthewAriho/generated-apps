"""Shared constants and mock/fallback data for CineQueue."""

# Default card color (RGBA tuple) used as fallback when no poster is available
CARD = (0.13, 0.13, 0.18, 1)

# TMDB CDN base URL (no auth needed for image serving)
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w342"

# Country code mappings
TMDB_COUNTRY = {
    'United States of America': 'US', 'United Kingdom': 'UK',
    'Japan': 'JP', 'South Korea': 'KR', 'France': 'FR',
    'Germany': 'DE', 'Italy': 'IT', 'Spain': 'ES', 'Australia': 'AU',
    'Canada': 'CA', 'Sweden': 'SE', 'Denmark': 'DK', 'Norway': 'NO',
    'Mexico': 'MX', 'Brazil': 'BR', 'India': 'IN', 'China': 'CN',
}

FLAG = {
    "JP": "\U0001f1ef\U0001f1f5", "KR": "\U0001f1f0\U0001f1f7",
    "FR": "\U0001f1eb\U0001f1f7", "UK": "\U0001f1ec\U0001f1e7",
    "US": "\U0001f1fa\U0001f1f8", "DE": "\U0001f1e9\U0001f1ea",
    "IT": "\U0001f1ee\U0001f1f9", "SE": "\U0001f1f8\U0001f1ea",
    "AU": "\U0001f1e6\U0001f1fa", "CN": "\U0001f1e8\U0001f1f3",
    "IN": "\U0001f1ee\U0001f1f3", "BR": "\U0001f1e7\U0001f1f7",
    "MX": "\U0001f1f2\U0001f1fd", "DK": "\U0001f1e9\U0001f1f0",
    "NO": "\U0001f1f3\U0001f1f4",
}

_T = TMDB_IMG_BASE

MOCK_PLEX = [
    {"title": "Blade Runner 2049", "year": 2017, "genre": "Sci-Fi", "country": "US",
     "rating": 8.0, "plex_added": "2024-01-15", "poster_color": (0.15, 0.20, 0.35, 1),
     "runtime": 164, "director": "Denis Villeneuve", "source": "plex",
     "poster_url": _T + "/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg"},
    {"title": "Parasite", "year": 2019, "genre": "Thriller", "country": "KR",
     "rating": 8.6, "plex_added": "2024-02-20", "poster_color": (0.20, 0.30, 0.15, 1),
     "runtime": 132, "director": "Bong Joon-ho", "source": "plex",
     "poster_url": _T + "/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg"},
    {"title": "The Grand Budapest Hotel", "year": 2014, "genre": "Comedy", "country": "US",
     "rating": 8.1, "plex_added": "2023-11-05", "poster_color": (0.40, 0.15, 0.30, 1),
     "runtime": 99, "director": "Wes Anderson", "source": "plex",
     "poster_url": _T + "/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg"},
    {"title": "Spirited Away", "year": 2001, "genre": "Animation", "country": "JP",
     "rating": 8.6, "plex_added": "2024-03-10", "poster_color": (0.10, 0.25, 0.40, 1),
     "runtime": 125, "director": "Hayao Miyazaki", "source": "plex",
     "poster_url": _T + "/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg"},
    {"title": "No Country for Old Men", "year": 2007, "genre": "Crime", "country": "US",
     "rating": 8.1, "plex_added": "2023-12-18", "poster_color": (0.30, 0.20, 0.10, 1),
     "runtime": 122, "director": "Coen Brothers", "source": "plex",
     "poster_url": _T + "/6d5XOczc2bqDMB3wBqBpTBQQiJa.jpg"},
    {"title": "Portrait of a Lady on Fire", "year": 2019, "genre": "Romance", "country": "FR",
     "rating": 8.1, "plex_added": "2024-01-28", "poster_color": (0.35, 0.10, 0.10, 1),
     "runtime": 122, "director": "Celine Sciamma", "source": "plex",
     "poster_url": _T + "/sygBh89OG7E0mBxBVmf3VwI2sXI.jpg"},
    {"title": "Everything Everywhere", "year": 2022, "genre": "Sci-Fi", "country": "US",
     "rating": 7.8, "plex_added": "2024-02-14", "poster_color": (0.25, 0.10, 0.35, 1),
     "runtime": 139, "director": "Daniels", "source": "plex",
     "poster_url": _T + "/w3LxiVYdWWRvEVdn5RYq6jIqkb1.jpg"},
    {"title": "The Lighthouse", "year": 2019, "genre": "Horror", "country": "US",
     "rating": 7.5, "plex_added": "2023-10-31", "poster_color": (0.20, 0.20, 0.20, 1),
     "runtime": 109, "director": "Robert Eggers", "source": "plex",
     "poster_url": _T + "/5EFh4QAKKtKtTMNDGnI4H8Ao3JH.jpg"},
]

MOCK_LB = [
    {"title": "Drive My Car", "year": 2021, "genre": "Drama", "country": "JP",
     "rating": 7.9, "lb_added": "2024-03-01", "poster_color": (0.10, 0.15, 0.30, 1),
     "runtime": 179, "director": "Ryusuke Hamaguchi", "source": "letterboxd",
     "poster_url": _T + "/oFMSsm7tl3VIF5GkLBSxdNnqVSX.jpg"},
    {"title": "The Favourite", "year": 2018, "genre": "Drama", "country": "UK",
     "rating": 7.5, "lb_added": "2024-02-10", "poster_color": (0.25, 0.25, 0.15, 1),
     "runtime": 119, "director": "Yorgos Lanthimos", "source": "letterboxd",
     "poster_url": _T + "/5k7bH2Mzm9k4LiRKHAHDGaI2fSP.jpg"},
    {"title": "Aftersun", "year": 2022, "genre": "Drama", "country": "UK",
     "rating": 7.7, "lb_added": "2024-01-05", "poster_color": (0.15, 0.30, 0.25, 1),
     "runtime": 101, "director": "Charlotte Wells", "source": "letterboxd",
     "poster_url": _T + "/s3VBKN5nCqJlgGORfT0MvdVJlhU.jpg"},
    {"title": "Tar", "year": 2022, "genre": "Drama", "country": "US",
     "rating": 7.5, "lb_added": "2024-03-15", "poster_color": (0.20, 0.15, 0.25, 1),
     "runtime": 158, "director": "Todd Field", "source": "letterboxd",
     "poster_url": _T + "/7j6uRfvGkgZzFw0SjFJTEqD5rVU.jpg"},
    {"title": "Cache", "year": 2005, "genre": "Thriller", "country": "FR",
     "rating": 7.7, "lb_added": "2024-02-28", "poster_color": (0.30, 0.25, 0.10, 1),
     "runtime": 117, "director": "Michael Haneke", "source": "letterboxd",
     "poster_url": _T + "/d9nBoowhjiiYc4FBNtQkPY7c11H.jpg"},
]

MOCK_WATCHED = [
    {"title": "Dune", "year": 2021, "date": "2024-03-20"},
    {"title": "The Batman", "year": 2022, "date": "2024-03-15"},
    {"title": "Past Lives", "year": 2023, "date": "2024-03-10"},
    {"title": "Oppenheimer", "year": 2023, "date": "2024-02-28"},
    {"title": "Poor Things", "year": 2023, "date": "2024-02-14"},
    {"title": "May December", "year": 2023, "date": "2024-02-05"},
    {"title": "Barbie", "year": 2023, "date": "2024-01-20"},
    {"title": "Saltburn", "year": 2023, "date": "2024-01-10"},
    {"title": "Priscilla", "year": 2023, "date": "2023-12-25"},
    {"title": "Monster", "year": 2023, "date": "2023-12-18"},
    {"title": "Killers of the Flower Moon", "year": 2023, "date": "2023-12-05"},
    {"title": "The Zone of Interest", "year": 2023, "date": "2023-11-30"},
]

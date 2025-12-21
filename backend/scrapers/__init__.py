# Ghana Bookmaker Scrapers
from .betway_ghana import scrape_betway_ghana
from .sportybet_ghana import scrape_sportybet_ghana
from .onexbet_ghana import scrape_1xbet_ghana
from .twentytwobet_ghana import scrape_22bet_ghana
from .soccabet_ghana import scrape_soccabet_ghana
from .betfox_ghana import scrape_betfox_ghana

__all__ = [
    'scrape_betway_ghana',
    'scrape_sportybet_ghana',
    'scrape_1xbet_ghana',
    'scrape_22bet_ghana',
    'scrape_soccabet_ghana',
    'scrape_betfox_ghana',
]

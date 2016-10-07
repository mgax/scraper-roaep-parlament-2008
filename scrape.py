from urllib.parse import quote
from hashlib import sha1
from pathlib import Path
import json
import csv
import requests

URL_PREFIX = 'http://alegeri.roaep.ro/wp-content/plugins/aep/'
CACHE_ROOT = Path(__file__).resolve().parent / 'cache'
OUT_ROOT = Path(__file__).resolve().parent / 'out'

CHAMBERS = [
    {'name': 'senat', 'code': 'S', 'id': 5},
    {'name': 'cdep', 'code': 'CD', 'id': 6},
]

CSV_FIELDS = [
    'county_name',
    'county_code',
    'college_code',
    'college_id',
    'party',
    'candidate',
    'votes',
    'percent',
]

class Cache:

    def __init__(self, key):
        hash = sha1(key.encode('utf-8')).hexdigest()
        path = CACHE_ROOT / hash[:2] / hash[2:4] / key
        self.path = path
        self.hit = path.is_file()
        if self.hit:
            with path.open('rt', encoding='utf-8') as f:
                self.data = json.load(f)

    def save(self, data):
        self.data = data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('wt', encoding='utf-8') as f:
            json.dump(data, f, sort_keys=True, indent=2)

class Client:

    def get_cache(self, url):
        return Cache(quote(url))

    def get(self, url):
        cache = self.get_cache(url)
        if not cache.hit:
            print('cache miss', url)
            resp = requests.get(URL_PREFIX + url)
            cache.save(resp.json())
        return cache.data

class VoteScraper:

    CHAMBERS_URL = 'aep_data.php?name=v1_parl_TipVoturi&parameter=248'
    COUNTIES_URL = ('aep_data.php?name=v1_parl_Judet_Lista&parameter=248'
        '&parameter={}')
    COLEGII_URL = ('aep_data.php?name=v1_parl_Colegii_Lista&parameter=248'
        '&parameter={}&parameter={}')
    RESULTS_URL = ('aep_data.php?name=v1_parl_Colegiu_Voturi&parameter=248'
        '&parameter={}&parameter={}&parameter={}')

    def __init__(self, client):
        self.client = client

    def run_college(self, chamber, county, college):
        results_url = self.RESULTS_URL.format(
            county['COD_JUD'], college['CodColegiu'], chamber['code'])
        for result in self.client.get(results_url):
            yield {
                'county_name': county['DEN_JUD'],
                'county_code': county['COD_JUD'],
                'college_id': college['Id'],
                'college_code': college['CodColegiu'],
                'party': result['DenumireScurta'],
                'candidate': result['Candidat'],
                'votes': result['Voturi'],
                'percent': result['Procent'],
            }

    def run_county(self, chamber, county):
        colegii_url = self.COLEGII_URL.format(
            county['COD_JUD'], chamber['code'])
        for college in self.client.get(colegii_url):
            yield from self.run_college(chamber, county, college)

    def get_chambers(self):
        return self.client.get(self.CHAMBERS_URL)

    def run(self, chamber):
        counties_url = self.COUNTIES_URL.format(chamber['id'])
        for county in self.client.get(counties_url):
            yield from self.run_county(chamber, county)

def save(name, fields, rows):
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    outfile = OUT_ROOT / '{}.csv'.format(name)
    with outfile.open('wt', encoding='utf-8') as f:
        out = csv.DictWriter(f, fields)
        out.writeheader()
        for row in rows:
            out.writerow(row)

def main():
    scraper = VoteScraper(Client())
    for chamber in CHAMBERS:
        save(chamber['name'], CSV_FIELDS, scraper.run(chamber))

if __name__ == '__main__':
    main()

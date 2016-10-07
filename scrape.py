import sys
from urllib.parse import quote
from hashlib import sha1
from pathlib import Path
import json
import csv
import requests

URL_PREFIX = 'http://alegeri.roaep.ro/wp-content/plugins/aep/'
CACHE_ROOT = Path(__file__).resolve().parent / 'cache'

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
        '&parameter=5')
    COLEGII_URL = ('aep_data.php?name=v1_parl_Colegii_Lista&parameter=248'
        '&parameter={}&parameter=S')
    RESULTS_URL = ('aep_data.php?name=v1_parl_Colegiu_Voturi&parameter=248'
        '&parameter={}&parameter={}&parameter=S')

    def __init__(self, client):
        self.client = client

    def run_college(self, county_code, college):
        college_code = college['CodColegiu']
        college_id = college['Id']
        results_url = self.RESULTS_URL.format(
            county_code, college_code)
        for result in self.client.get(results_url):
            yield {
                'county_code': county_code,
                'college_id': college_id,
                'college_code': college_code,
                'party': result['DenumireScurta'],
                'candidate': result['Candidat'],
                'votes': result['Voturi'],
                'percent': result['Procent'],
            }

    def run_county(self, county):
        county_code = county['COD_JUD']
        county_name = county['DEN_JUD']
        colegii_url = self.COLEGII_URL.format(county_code)
        for college in self.client.get(colegii_url):
            for row in self.run_college(county_code, college):
                yield dict(row, county_name=county_name)

    def run(self):
        for chamber in self.client.get(self.CHAMBERS_URL):
            for county in self.client.get(self.COUNTIES_URL):
                yield from self.run_county(county)

def main():
    fields = [
        'county_name',
        'county_code',
        'college_code',
        'college_id',
        'party',
        'candidate',
        'votes',
        'percent',
    ]
    out = csv.DictWriter(sys.stdout, fields)
    out.writeheader()
    for row in VoteScraper(Client()).run():
        out.writerow(row)

if __name__ == '__main__':
    main()

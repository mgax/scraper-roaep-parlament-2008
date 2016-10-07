from urllib.parse import quote
from hashlib import sha1
from pathlib import Path
import json
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

    def __init__(self, client):
        self.client = client

    def run(self):
        counties = self.client.get(self.COUNTIES_URL)
        for chamber in self.client.get(self.CHAMBERS_URL):
            for county in counties:
                colegii_url = self.COLEGII_URL.format(county['COD_JUD'])
                for colegiu in self.client.get(colegii_url):
                    print(colegiu['CodColegiu'])
                    return

def main():
    VoteScraper(Client()).run()

if __name__ == '__main__':
    main()

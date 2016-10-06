import requests

URL_PREFIX = 'http://alegeri.roaep.ro/wp-content/plugins/aep/'

class Client:

    def get(self, url):
        resp = requests.get(URL_PREFIX + url)
        print(resp.json())

def main():
    c = Client()
    c.get('aep_data.php?name=v1_parl_TipVoturi&parameter=248')

if __name__ == '__main__':
    main()

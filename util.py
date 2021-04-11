import re

from bs4 import BeautifulSoup
from ratelimit import limits, sleep_and_retry
from requests import get
from tqdm import tqdm
from yaml import dump
from toolz.curried import comp

data_path = 'data.yaml'

def download_data():
    country_list_url = 'https://simple.wikipedia.org/wiki/List_of_European_countries'
    border_list_url = 'https://en.wikipedia.org/wiki/List_of_countries_and_territories_by_land_borders'
    base_url = 'https://en.wikipedia.org/wiki/'
    wikilimiter = comp(sleep_and_retry, limits(1, 1))

    @wikilimiter
    def download_countries():
        country_list_page = BeautifulSoup(get(country_list_url).text, features='html.parser')
        country_table = [row.find_all('a', href=re.compile(r'^/wiki/'))[1:]
                         for row in country_list_page.find('tbody').find_all('tr')[1:]]
        return {str(a[0].string): str(a[-1]['href']).replace('/wiki/', '') for a in country_table}

    @wikilimiter
    def download_borders():
        border_list_page = BeautifulSoup(get(border_list_url).text, features='html.parser')
        return dict(((q:=[str(a.string) for a in row.find_all('a', href=re.compile(r'^/wiki/')) if str(a.string)[0].isupper()])[0], q[1:])
                    for row in border_list_page.find('tbody').find_all('tr')[2:] if not ('overseas' in str(row) and 'excluding' not in str(row)))

    @wikilimiter
    def download_coords(capital):
        capital_page = BeautifulSoup(get(base_url + capital).text, features='html.parser')
        return list(map(float, capital_page.find('span', class_='geo').string.split(';')))

    countries = download_countries()
    borders = download_borders()
    borders['Cyprus'] = [] # for some reason uk gets listed here but not for spain, dirty hack but it works

    full_data =   {country: {'loc': download_coords(capital),
                             'neighs': [neigh for neigh in borders[country] if neigh in countries]
                             } for country, capital in tqdm(countries.items())}
    with open(data_path, 'w') as data_file:
        dump(full_data, data_file)

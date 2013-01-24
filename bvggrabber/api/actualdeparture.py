# -*- coding: utf-8 -*-


import requests

from bs4 import BeautifulSoup

from bvggrabber.api import QueryApi, Departure


ACTUAL_QUERY_API_ENDPOINT = 'http://mobil.bvg.de/IstAbfahrtzeiten/index/mobil'


class ActualDepartureQueryApi(QueryApi):

    def __init__(self, station):
        super(ActualDepartureQueryApi, self).__init__()
        if isinstance(station, str):
            self.station_enc = station.encode('iso-8859-1')
        elif isinstance(station, bytes):
            self.station_enc = station
        else:
            raise ValueError("Invalid type for station")
        self.station = station

    def call(self):
        params = {'input': self.station_enc}
        response = requests.get(ACTUAL_QUERY_API_ENDPOINT, params=params)
        if response.status_code == requests.codes.ok:
            soup = BeautifulSoup(response.text)
            if soup.find_all('form'):
                # The station we are looking for is ambiguous or does not exist
                stations = soup.find_all('option')
                if stations:
                    # The station is ambiguous
                    stationlist = [s.get('value') for s in stations]
                    return (False, stationlist)
                else:
                    # The station does not exist
                    return (False, [])
            else:
                # The station seems to exist
                rows = soup.find('tbody').find_all('tr')
                departures = []
                for row in rows:
                    tds = row.find_all('td')
                    dep = Departure(start=self.station,
                                    end=tds[2].text.strip(),
                                    line=tds[1].text.strip())
                    departures.append(dep)
                return (True, departures)
        else:
            response.raise_for_status()
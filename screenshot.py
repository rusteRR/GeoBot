import sys
from io import BytesIO
import requests
from PIL import Image
import pprint


class Map:
    def get_coords(self, toponym_to_find):
        geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"

        geocoder_params = {
            "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
            "geocode": toponym_to_find,
            "format": "json"}

        response = requests.get(geocoder_api_server, params=geocoder_params)

        if not response:
            pass

        json_response = response.json()

        toponym = json_response["response"]["GeoObjectCollection"][
            "featureMember"][0]["GeoObject"]
        toponym_coodrinates = toponym["Point"]["pos"]
        toponym_longitude, toponym_lattitude = toponym_coodrinates.split(" ")
        lower = json_response['response']['GeoObjectCollection']['featureMember'][0][
            'GeoObject']['boundedBy']['Envelope']['lowerCorner']
        upper = json_response['response']['GeoObjectCollection']['featureMember'][0][
            'GeoObject']['boundedBy']['Envelope']['upperCorner']
        return upper, lower, toponym_lattitude, toponym_longitude

    def draw_map(self, toponym_to_find):
        upper, lower, toponym_lattitude, toponym_longitude = self.get_coords(
            toponym_to_find)
        x0, y0 = tuple(map(float, lower.split()))
        x1, y1 = tuple(map(float, upper.split()))
        deltaX = (x1 - x0) * 0.25
        deltaY = (y1 - y0) * 0.25
        delta = str(max(deltaX, deltaY))
        print(lower)

        map_params = {
            "ll": ",".join([toponym_longitude, toponym_lattitude]),
            "spn": ",".join([delta, delta]),
            "l": "sat"
        }

        map_api_server = "http://static-maps.yandex.ru/1.x/"
        # ... и выполняем запрос
        response = requests.get(map_api_server, params=map_params)

        return (BytesIO(response.content))

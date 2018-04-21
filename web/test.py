# coding: utf-8

import requests

alert = {}

url = "http://127.0.0.1:8087/ViewGraphDetail.do"
alert["metric_name"] = 'temperature.cpu'
alert["tags_name"] = 'host=127.0.0.1,cpu=cpu11'

# alert["metric_name"] = 'iostat.disk.read_requests'
# alert["tags_name"] = 'host=~/.*PCCW.*/,dev=~/sd.*/'
alert["slug"] = 'disk'
alert["page_num"] = '0'

try:
    print(alert)
    req = requests.post(url, data=alert)
    print(req.status_code)
    print(req.text)
except requests.exceptions.RequestException as e:
    print(e)


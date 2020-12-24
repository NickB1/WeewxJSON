#!/usr/bin/env python

from __future__ import with_statement
from __future__ import absolute_import
from __future__ import print_function

import time
import json
import requests
from datetime import datetime

import weewx.drivers
import weeutil.weeutil

DRIVER_NAME = 'weewxJSON'
DRIVER_VERSION = '1.0'

DEFAULT_URL = 'http://your-ip/password/get-sensors'
LOOP_INTERVAL = 10


def loader(config_dict, _):
    return weewxJSON(**config_dict[DRIVER_NAME])


def confeditor_loader():
    return weewxJSONConfEditor()

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'weewxJSON: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)


class weewxJSON(weewx.drivers.AbstractDevice):
    def __init__(self, **stn_dict):
        self.model = stn_dict.get('model', 'weewxJSON')
        self.loop_interval = float(stn_dict.get('loop_interval', LOOP_INTERVAL))
        self.url = stn_dict.get('url', DEFAULT_URL)
        self.max_tries = int(stn_dict.get('max_tries', 10))
        self.retry_wait = float(stn_dict.get('retry_wait', 10))

        loginf('driver version is %s' % DRIVER_VERSION)
        loginf('using url %s' % self.url)
        self.station = Station(self.url)

    @property
    def hardware_name(self):
        return self.model

    def genLoopPackets(self):
        while True:
            packet = {'dateTime': int(time.time() + 0.5),
                      'usUnits': weewx.METRICWX}
            json_data = self.station.json_read_url_with_retry(self.max_tries, self.retry_wait)
            #data = Station.parse_readings(self.station, json_data)
            if json_data:
                packet.update(json_data)
                yield packet
            time.sleep(self.loop_interval)


class Station(object):
    def __init__(self, url):
        self.url = url
        self.timeout = 30

    def json_read_url(self):
        try:
            data = requests.get(self.url)
            return data.json()
        except requests.exceptions.RequestException as e:
            print("URL Error")

    def json_read_url_with_retry(self, max_tries=5, retry_wait=10):
        for retries in range(0, max_tries):
            try:
                data = requests.get(self.url, timeout=retry_wait)  # , timeout=10
            except requests.exceptions.RequestException as e:
                loginf("Failed attempt %d of %d to get json data: %s" %
                       (retries + 1, max_tries, e))
                # time.sleep(retry_wait)
            else:
                # return parse_readings(self, data.json())
                return self.parse_readings(self, data.json())
        else:
            msg = "Max retries (%d) exceeded for readings" % max_tries
            logerr(msg)
            raise weewx.RetriesExceeded(msg)

    @staticmethod
    def json_read_file(self, path):
        with open(path) as json_file:
            data = json.load(json_file)
            return data

    @staticmethod
    def json_print(self, json_file):
        print(json.dumps(json_file, indent=2, sort_keys=True))

    @staticmethod
    def get_degrees_number(self, text):
        degrees = [int(s) for s in text.split() if s.isdigit()]
        return degrees

    @staticmethod
    def rotate_degrees(self, angle, rotate_angle):
        angle = angle + rotate_angle
        while angle >= 360:
            angle = angle - 360
        return angle

    @staticmethod
    def deg_to_compass(self, num):
        val = int((num / 22.5) + .5)
        arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        return arr[(val % 16)]

    @staticmethod
    def parse_readings(self, json_data):
        data = dict()
        try:
            wind_direction = json_data['response']['windmeters'][0]['dir']
            #[wind_direction] = self.get_degrees_number(self, json_data['response']['windmeters'][0]['dir'])
            #wind_direction_corrected = self.rotate_degrees(self, wind_direction, 0)
            wind_speed = json_data['response']['windmeters'][0]['ws']
            wind_speed_gust = json_data['response']['windmeters'][0]['gu']
            temperature = json_data['response']['windmeters'][0]['te']
        except (ValueError, KeyError) as e:
            logerr("JSON parsing error")
        else:
            data['windDir'] = self.get_degrees_number(self, wind_direction)[0]
            #data['windDir'] = wind_direction_corrected
            data['windSpeed'] = wind_speed
            data['windGust'] = wind_speed_gust
            data['outTemp'] = temperature

        return data


class weewxJSONConfEditor(weewx.drivers.AbstractConfEditor):
    @property
    def default_stanza(self):
        return """
[weewxJSON]
    # This section is for weewxJSON
    # The time (in seconds) between LOOP packets.
    loop_interval = 10
    # The url to get the JSON packet from
    # url = http://yoursite.com/get-json
    # The driver to use:
    driver = weewx.drivers.weewxJSON
"""

    def prompt_for_settings(self):
        print("Specify the json url")
        print("example http://url.test")
        url = self._prompt('url', 'http://url.test')
        return {'url': url}


if __name__ == '__main__':
    import optparse

    usage = """%prog [options] [--help]"""

    syslog.openlog('weewxJSON', syslog.LOG_PID | syslog.LOG_CONS)
    syslog.setlogmask(syslog.LOG_UPTO(syslog.LOG_DEBUG))
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('--version', dest='version', action='store_true',
                      help='display driver version')
    parser.add_option('--url', dest='url', metavar='URL',
                      help='url to get data from',
                      default=DEFAULT_URL)
    (options, args) = parser.parse_args()

    if options.version:
        print("weewxJSON driver version %s" % DRIVER_VERSION)
        exit(0)

    with Station(options.url) as s:
        while True:
            print(time.time(), s.get_readings())

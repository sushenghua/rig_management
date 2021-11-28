#!/usr/bin/env python3

import requests
import redis
import json
import pwr_light_sensor as pwrlight
import sht3x_sensor as sht3x
import pm_sensor as pms
import time
# import datetime


#--------------------------------------------------------------------
# ------------------ redis
REDIS_SERVER_HOST = '127.0.0.1'
REDIS_SERVER_PORT = 6379
REDIS_SERVER_PASS = 'rigConnection@ip64'
r = redis.StrictRedis(host=REDIS_SERVER_HOST, port=REDIS_SERVER_PORT,
                      db=0, password=REDIS_SERVER_PASS)


#--------------------------------------------------------------------
# ------------------ sensor
pmsi = pms.PMSensor.instance()


#--------------------------------------------------------------------
# ------------------ sensor
IFTTT_URL = 'https://maker.ifttt.com/trigger/Farm%20Pi/json/with/key/bHJWJJ7yWpgGb77sMugjyd'
IFTTT_HEADER = {'Content-type': 'application/json', 'Accept': 'text/plain'}


#--------------------------------------------------------------------
# ------------------ gpu standard
GPU_STD = {
  'RTX 3060': {
    'hashrate_avr': 34000000,
    'hashrate_low': 20000000,
    'temp_high':    70
  },
  'RTX 3070': {
    'hashrate_avr': 44000000,
    'hashrate_low': 30000000,
    'temp_high':    70 
  },
  'RTX 3080': {
    'hashrate_avr': 74000000,
    'hashrate_low': 40000000,
    'temp_high':    70 
  }
}


#--------------------------------------------------------------------
# ------------------ ifttt msg limit
IFTTT_MSG_MAX_COUNT       = 6
IFTTT_MSG_TIME_INTERVAL   = 30
IFTTT_MSG_MAX_COUNT_WAIT  = 60 * 30 # half hour


#--------------------------------------------------------------------
# ------------------ class
CHECK_SLEEP_TIME    = 5  # check every 5 seconds
RIGINFO_KEY         = 'riginfo'

class RigStatusMonitor():

  def __init__(self):
    self._riginfo = None
    self.rig_info()
    self._nobeat_count = 0
    self._ifttt_send_time = 0
    self._ifttt_send_count = 0

  def rig_info(self):
    if self._riginfo is None:
      if r.exists(RIGINFO_KEY) > 0:
        self._riginfo = json.loads(r.get(RIGINFO_KEY))
      else:
        print('no riginfo found in redis')
    return self._riginfo

  def sample_external_status(self):
    # --- temperature, humidity
    th = None
    try:
      th = sht3x.read_dict_data()
    except Exception as e:
      print('th err: ', e)
      th = sht3x.invalid_dict_data()
    else:
      pass
    finally:
      pass
    # --- power status
    ps = None
    try:
      ps = pwrlight.ison()
    except Exception as e:
      print('ps err: ', e)
      ps = pwrlight.invalid_status()
    else:
      pass
    finally:
      pass
    # --- pm data
    pm = None
    try:
      pm = pmsi.read().dict_data()
    except Exception as e:
      print('pm err: ', e)
      pm = pms.invalid_pm_dict_data()
    else:
      pass
    finally:
      pass
    # --- result obj
    ret = {
      'th': th,
      'ps': ps,
      'pm': pm
    }
    return ret

  def sample_internal_status(self):
    try:
      beatkey = self._riginfo['beatkey']
      if r.exists(beatkey) > 0:
        rigbeat = json.loads(r.get(beatkey))
        # print(rigbeat['time'])
      else:
        print('no key: ', beatkey)
        rigbeat = None
    except Exception as e:
      rigbeat = None
      print('monitor err: ', e)
    finally:
      return rigbeat

  def single_check():
    try:
      # print(json.dumps(sample()))
      riginfo = r.get('riginfo')
      print(riginfo)
      info_obj = json.loads(riginfo)
      beatkey = info_obj['beatkey']
      if r.exists(beatkey) > 0:
        rigbeat = json.loads(r.get(beatkey))
        print(rigbeat['time'])
      else:
        print('no key: ', beatkey)

    except Exception as e:
      print('monitor err: ', e)


  def _check_gpus(self, gpus):
    hashrate_warnings = []
    temp_warnings = []
    for gpu in gpus:
      if gpu['hashrate'] < GPU_STD[gpu['name']]['hashrate_low']:
        hashrate_warnings.append(''.join([gpu['name'], ' low hashrate: [', str(gpu['hashrate']), ']']))
      if gpu['temperature'] > GPU_STD[gpu['name']]['temp_high']:
        temp_warnings.append(''.join([gpu['name'], ' high temp: [', str(gpu['temperature']), ']']))
    return hashrate_warnings, temp_warnings

  def _check_data(self, data):
    h_warnings, t_warnings = self._check_gpus(data['gpus'])
    if len(h_warnings) > 0 or len(t_warnings) > 0:
      msg = {}
      if  len(h_warnings) > 0:
        msg['hashrate'] = h_warnings
      if  len(t_warnings) > 0:
        msg['temp'] = t_warnings
      self.send_ifttt_msg('warning', msg)

  def check_loop(self):

    while True:
      if self.rig_info():
        ret = self.sample_internal_status()
        if ret:
          #print(ret)
          print('------ check', self.rig_info()['name'], '------')
          # print(ret['hashrate'])
          self._check_data(ret)
        else:
          print('no status data found for rig: ', self.rig_info()['name'])
          pass
      else:
        print('no rig info found')

      # --- wait net check cycle
      time.sleep(CHECK_SLEEP_TIME)

  def send_ifttt_msg(self, title, msg):
    timenow = time.time()

    if timenow - self._ifttt_send_time >= IFTTT_MSG_MAX_COUNT_WAIT:
      self._ifttt_send_count = 0

    if self._ifttt_send_count < IFTTT_MSG_MAX_COUNT:
      if timenow - self._ifttt_send_time >= IFTTT_MSG_TIME_INTERVAL:
        self._ifttt_send_time = timenow
        self._ifttt_send_count += 1
        jsondata = json.dumps({title: msg})
        requests.post(IFTTT_URL, data=jsondata, headers=IFTTT_HEADER)

def test():
  rsm = RigStatusMonitor()
  rsm.check_loop()

test()

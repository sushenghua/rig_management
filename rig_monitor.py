#!/usr/bin/env python3

import requests
import redis
import json
import time


#--------------------------------------------------------------------
# ------------------ redis
REDIS_SERVER_HOST = '127.0.0.1'
REDIS_SERVER_PORT = 6379
REDIS_SERVER_PASS = 'rigConnection@ip64'
r = redis.StrictRedis(host=REDIS_SERVER_HOST, port=REDIS_SERVER_PORT,
                      db=0, password=REDIS_SERVER_PASS)


#--------------------------------------------------------------------
# ------------------ ifttt msg class
# --- IFTTT format
IFTTT_URL = 'https://maker.ifttt.com/trigger/yourlink'
IFTTT_HEADER = {'Content-type': 'application/json', 'Accept': 'text/plain'}

# --- send limit
IFTTT_MSG_COUNT_MAX       = 2         # 6 times max
IFTTT_MSG_COUNT_MAX_CD    = 60 * 10   # check every 10 min
IFTTT_MSG_TIME_INTERVAL   = 30        # 30 seconds
IFTTT_ERR_MSG_COUNT_MAX   = 2         # 3 times max


class IftttMsgSendSession():

  def __init__(self, count_max=IFTTT_MSG_COUNT_MAX,
                     count_max_cd=IFTTT_MSG_COUNT_MAX_CD,
                     time_interval=IFTTT_MSG_TIME_INTERVAL):
    self._send_count_max = count_max
    self._send_count_max_cd = count_max_cd
    self._send_time_interval = time_interval
    self._send_count = 0
    self._send_time = 0

  def send_msg(self, title, msg):
    timenow = time.time()

    if timenow - self._send_time >= self._send_count_max_cd:
      print('reset cd')
      self._send_count = 0

    if self._send_count < self._send_count_max:
      print('count ok')
      if timenow - self._send_time >= self._send_time_interval:
        print('interval ok')
        self._send_time = timenow
        self._send_count += 1
        print('send count', self._send_count)
        jsondata = json.dumps({title: msg})
        requests.post(IFTTT_URL, data=jsondata, headers=IFTTT_HEADER)


#--------------------------------------------------------------------
# ------------------ pm, th, ps standard
PM_TH_PS_STD = {
  # 'pm2d5_high':     100,  # 100: index value will be above 175
  'pm2d5_high':     35,  # 35: index value will be above 99
  'pm10d_high':     150,
  'temp_in_high':   30,
  'temp_out_high':  38,
  'humid_in_high':  70,
  'ps_off':         False
}


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
# ------------------ monitor class
CHECK_SLEEP_TIME    = 5  # check every 5 seconds
RIG_INFO_KEY        = 'riginfo'
RIG_EX_INFO_KEY     = 'rigexinfo'

class RigStatusMonitor():

  def __init__(self):
    self._rig_info = None
    self._rig_ex_info = None
    self.rig_info()
    self.rig_ex_info()
    self._nobeat_count = 0
    self._ifttt_internal_normal_msg = IftttMsgSendSession()
    self._ifttt_internal_err_msg = IftttMsgSendSession(count_max=IFTTT_ERR_MSG_COUNT_MAX)
    self._ifttt_external_normal_msg = IftttMsgSendSession()
    self._ifttt_external_err_msg = IftttMsgSendSession(count_max=IFTTT_ERR_MSG_COUNT_MAX)


  def rig_info(self):
    if self._rig_info is None:
      if r.exists(RIG_INFO_KEY) > 0:
        self._rig_info = json.loads(r.get(RIG_INFO_KEY))
      else:
        print('no riginfo found in redis')
    return self._rig_info

  def rig_ex_info(self):
    if self._rig_ex_info is None:
      if r.exists(RIG_EX_INFO_KEY) > 0:
        self._rig_ex_info = json.loads(r.get(RIG_EX_INFO_KEY))
      else:
        print('no rigexinfo found in redis')
    return self._rig_ex_info

  # ------ obtain and check external data
  def obtain_external_status(self):
    try:
      beatkey = self._rig_ex_info['beatkey']
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

  def _check_pm_th_ps(self, data):
    pm_warnings = []
    th_warnings = []
    ps_warnings = []

    pm2d5 = data['pm']['ugpm3']['2d5']
    pm10d = data['pm']['ugpm3']['10d']
    if pm2d5 > PM_TH_PS_STD['pm2d5_high']:
      pm_warnings.append(''.join(['PM2.5 High: [', str(pm2d5), ']']))
    if pm10d > PM_TH_PS_STD['pm10d_high']:
      pm_warnings.append(''.join(['PM10.0 High: [', str(pm10d), ']']))

    t_in = data['th']['up']['t']
    t_out = data['th']['down']['t']
    h_in = data['th']['up']['h']
    if t_in > PM_TH_PS_STD['temp_in_high']:
      th_warnings.append(''.join(['Air in temp high: [', str(t_in), ']']))
    if t_out > PM_TH_PS_STD['temp_out_high']:
      th_warnings.append(''.join(['Air out temp high: [', str(t_out), ']']))
    if h_in > PM_TH_PS_STD['humid_in_high']:
      th_warnings.append(''.join(['Air in humid high: [', str(h_in), ']']))

    if not data['ps']:
      print('---> ps off')
      ps_warnings.append('power off')

    return pm_warnings, th_warnings, ps_warnings

  def _check_external_data(self, data):
    pm_warnings, th_warnings, ps_warnings = self._check_pm_th_ps(data)
    # print('------ check', self.rig_info()['name'], 'external ------')
    if len(pm_warnings) > 0 or len(th_warnings) > 0 or len(ps_warnings) > 0:
      msg = {}
      if len(pm_warnings) > 0:
        msg['pm'] = pm_warnings
      if len(th_warnings) > 0:
        msg['th'] = th_warnings
      if len(ps_warnings) > 0:
        msg['ps'] = ps_warnings
      self._ifttt_external_normal_msg.send_msg(self.rig_info()['name'] + ' ex warning', msg)

  # ------ obtain and check internal data
  def obtain_internal_status(self):
    try:
      beatkey = self._rig_info['beatkey']
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
        hashrate_warnings.append(''.join([gpu['name'], ' LHR: [', str(gpu['hashrate']), ']']))
      if gpu['temperature'] > GPU_STD[gpu['name']]['temp_high']:
        temp_warnings.append(''.join([gpu['name'], ' HT: [', str(gpu['temperature']), ']']))
    return hashrate_warnings, temp_warnings

  def _check_internal_data(self, data):
    h_warnings, t_warnings = self._check_gpus(data['gpus'])
    if len(h_warnings) > 0 or len(t_warnings) > 0:
      msg = {}
      if  len(h_warnings) > 0:
        msg['hashrate'] = h_warnings
      if  len(t_warnings) > 0:
        msg['temp'] = t_warnings
      self._ifttt_internal_normal_msg.send_msg(self.rig_info()['name'] + ' warning', msg)

  # ------ check loop
  def check_loop(self):

    while True:
      if self.rig_info():
        ret = self.obtain_internal_status()
        if ret:
          #print(ret)
          # print('------ check', self.rig_info()['name'], '------')
          # print(ret['hashrate'])
          self._check_internal_data(ret)
        else:
          print('no status data found for rig: ', self.rig_info()['name'])
          self._ifttt_internal_err_msg.send_msg(self.rig_info()['name'] + ' warning', 'no status data received')
          pass
      else:
        print('no rig info found')
        self._ifttt_internal_err_msg.send_msg('err', 'no rig info found')

      if self.rig_ex_info():
        ret = self.obtain_external_status()
        if ret:
          print(ret)
          # print('------ check', self.rig_info()['name'], '------')
          # print(ret['hashrate'])
          self._check_external_data(ret)
        else:
          print('no status data found for rig ex: ', self.rig_ex_info()['name'])
          self._ifttt_external_err_msg.send_msg(self.rig_ex_info()['name'] + ' warning', 'no status data received')
          pass
      else:
        print('no rig ex info found')
        self._ifttt_external_err_msg.send_msg('err', 'no rig ex info found')

      # --- wait net check cycle
      time.sleep(CHECK_SLEEP_TIME)


# ------ app
def app():
  rsm = RigStatusMonitor()
  rsm.check_loop()

app()

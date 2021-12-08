#!/usr/bin/env python3

import time
from datetime import datetime
import json
import socket
import redis
import sys

import config as cfg
import pwr_light_sensor as pwrlight
import sht3x_sensor as sht3x
import pm_sensor as pms

#--------------------------------------------------------------------
# ------------------ sensor
pmsi = pms.PMSensor.instance()


#--------------------------------------------------------------------
# ------------------ settings
BEAT_PERIOD           = 5
BEAT_ALIVE_THRESHOLD   = 60  # be problematic if no beat in this time

LOG_MSG_5S_EXPIRE     = 60 * 120      # keep 2 hours
LOG_MSG_1M_EXPIRE     = 60 * 60 * 24  # keep 1 day

LOG_1M_PERIOD         = 60
LOG_1M_PEROID_DEV     = 5

KEEP_ERROR_TIME       = 60 * 60 * 24


#--------------------------------------------------------------------
# ------------------ redis
REDIS_SERVER_HOST = '127.0.0.1'
REDIS_SERVER_PORT = 6379
REDIS_SERVER_PASS = 'rigConnection@ip64'
r = redis.StrictRedis(host=REDIS_SERVER_HOST, port=REDIS_SERVER_PORT,
                      db=0, password=REDIS_SERVER_PASS)


#--------------------------------------------------------------------
# ------------------ exception classes
class RIG_RAW_DATA_ERR(RuntimeError):
  pass


#--------------------------------------------------------------------
# ------------------ methods

def release_resource():
  pmsi.release_resource()

def load_raw():
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

  time.sleep(0.2)
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

  time.sleep(0.2)
  # --- pm data
  pm = None
  try:
    pmsi.serial_open()
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
    'pm': pm,
    'time': int(time.time())
  }
  return ret

def _construct_key(t):
  id = str(t)
  rig_beat = cfg.RIG_NAME + '_beat'
  rig_5s = cfg.RIG_NAME + '_5s_' + id
  rig_1m = cfg.RIG_NAME + '_1m_' + id
  return rig_beat, rig_5s, rig_1m

def _beat_key():
  return cfg.RIG_NAME + '_beat'

def _rig_name():
  return cfg.RIG_NAME

def _err_key():
  return cfg.RIG_NAME + '_err'

def log_beat():

  time_to_beat = BEAT_PERIOD
  try:
    msg = load_raw()
    print(msg)

    # --- json format msg
    jsonmsg = json.dumps(msg)

    # --- update beat msg
    r.set(_beat_key(), jsonmsg, BEAT_ALIVE_THRESHOLD)
    r.set('th_ps_pm', jsonmsg, 6)  # for rig cmd easy access

    # --- align beat time point
    time_to_beat = msg['time'] % BEAT_PERIOD

  except Exception as e:
    print('log beat err:', e)
    rig_beat_err_key = _err_key()
    errmsg = {'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
              'err': str(e) }
    r.set(rig_beat_err_key, json.dumps(errmsg), KEEP_ERROR_TIME)

  else:
    pass

  finally:
    # test = r.get(rig_beat_key)
    # print(json.loads(test)['time'])
    pass

  # --- calculate next beat wait
  time_to_beat = time_to_beat if time_to_beat > 0 else BEAT_PERIOD
  # print('time to beat', time_to_beat)
  return time_to_beat


def cache_host_info():
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
  except Exception:
    ip = '127.0.0.1'
  finally:
    s.close()

  info = {
    'name':     _rig_name(),
    'hostname': socket.gethostname(),
    'lanip':    ip,
    'errkey':   _err_key(),
    'beatkey':  _beat_key()
  }
  print(info)
  r.set('rigexinfo', json.dumps(info))


#--------------------------------------------------------------------
# ------------------ procedure

# --- store host info to redis
cache_host_info()

# --- beat log loop
while True:
  try:
    align_wait = log_beat()
    time.sleep(align_wait)
  except KeyboardInterrupt:
    release_resource()
    # print(' program going to quit')
    sys.exit()


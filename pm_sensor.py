from pigpio_singleton import PiGpio
import pin_config as PIN
import serial
import struct
import time


#--------------------------------------------------------------------
# ------------------ PMSensorData
class PMSensorData():
  def __init__(self, raw_data):
    self.raw_data = raw_data
    self.data = struct.unpack(">HHHHHHHHHHHHH", raw_data)

  def pm_ug_per_m3(self, size, atmospheric_environment=False):
    if atmospheric_environment:
      if size == 1.0:
        return self.data[3]
      if size == 2.5:
        return self.data[4]
      if size is None:
        return self.data[5]

    else:
      if size == 1.0:
        return self.data[0]
      if size == 2.5:
        return self.data[1]
      if size == 10:
        return self.data[2]

    raise ValueError("Particle size {} measurement not available.".format(size))

  def pm_per_100ml_air(self, size):
    if size == 0.3:
      return self.data[6]
    if size == 0.5:
      return self.data[7]
    if size == 1.0:
      return self.data[8]
    if size == 2.5:
      return self.data[9]
    if size == 5:
      return self.data[10]
    if size == 10:
      return self.data[11]

    raise ValueError("Particle size {} measurement not available.".format(size))

  def dict_data(self):
    return {
      'ugpm3': {    # ugpm3: pm_ug_per_m3
        '1d0': self.data[0],
        '2d5': self.data[1],
        '10d': self.data[2]
      },
      'ctp100': {   # ctp100: above_um_count_per_100ml_air
        '0d3': self.data[6],
        '0d5': self.data[7],
        '1d0': self.data[8],
        '2d5': self.data[9],
        '5d0': self.data[10],
        '10d': self.data[11]
      }
    }

  def __repr__(self):
    return """
      PM1.0 ug/m3 (ultrafine particles):                             {}
      PM2.5 ug/m3 (combustion particles, organic compounds, metals): {}
      PM10  ug/m3 (dust, pollen, mould spores):                      {}
      PM1.0 ug/m3 (atmos env):                                       {}
      PM2.5 ug/m3 (atmos env):                                       {}
      PM10  ug/m3 (atmos env):                                       {}
      > 0.3um in 100ml air:                                          {}
      > 0.5um in 100ml air:                                          {}
      > 1.0um in 100ml air:                                          {}
      > 2.5um in 100mL air:                                          {}
      > 5.0um in 100ml air:                                          {}
      >10.0um in 100ml air:                                          {}
      """.format(*self.data[:])

  def __str__(self):
    return self.__repr__()


#--------------------------------------------------------------------
# ------------------ pm data method
INVALID_VAL = -999
def invalid_pm_dict_data():
  return {
    'ugpm3': {    # ugpm3: pm_ug_per_m3
      '1d0': INVALID_VAL,
      '2d5': INVALID_VAL,
      '10d': INVALID_VAL
    },
    'ctp100': {   # ctp100: above_um_count_per_100ml_air
      '0d3': INVALID_VAL,
      '0d5': INVALID_VAL,
      '1d0': INVALID_VAL,
      '2d5': INVALID_VAL,
      '5d0': INVALID_VAL,
      '10d': INVALID_VAL
    }
  }


def to_str(data):
  return """
    PM1.0 ug/m3 (ultrafine particles):                             {}
    PM2.5 ug/m3 (combustion particles, organic compounds, metals): {}
    PM10  ug/m3 (dust, pollen, mould spores):                      {}
    PM1.0 ug/m3 (atmos env):                                       {}
    PM2.5 ug/m3 (atmos env):                                       {}
    PM10  ug/m3 (atmos env):                                       {}
    > 0.3um in 100ml air:                                          {}
    > 0.5um in 100ml air:                                          {}
    > 1.0um in 100ml air:                                          {}
    > 2.5um in 100mL air:                                          {}
    > 5.0um in 100ml air:                                          {}
    >10.0um in 100ml air:                                          {}
    """.format(data['ugpm3']['1d0'], data['ugpm3']['2d5'], data['ugpm3']['10d'],
               data['ugpm3']['1d0'], data['ugpm3']['2d5'], data['ugpm3']['10d'],
               data['ctp100']['0d3'], data['ctp100']['0d5'], data['ctp100']['1d0'],
               data['ctp100']['2d5'], data['ctp100']['5d0'], data['ctp100']['10d'],
               )

#--------------------------------------------------------------------
# ------------------ exception classes
class PMFrameDataReadTimeoutError(RuntimeError):
  pass

class PMFrameDataCorruptError(RuntimeError):
  pass


#--------------------------------------------------------------------
# ------------------ pi gpio
pi = PiGpio.instance().pi()


#--------------------------------------------------------------------
# ------------------ PMSensor

# --- PMS5003x data format
PM_DATA_FRAME_HEAD = bytearray(b'\x42\x4d')
PM_DATA_FRAME_LEN = 32

# --- PMS5003 CMD
PASSIVE_READ            = b'\x42\x4d\xe2\x00\x00\x01\x71'
SWITCH_TO_PASSIVE_MODE  = b'\x42\x4d\xe1\x00\x00\x01\x70'
SWITCH_TO_ACTIVE_MDOE   = b'\x42\x4d\xe1\x00\x01\x01\x71'
SWITCH_TO_STANDBY_MODE  = b'\x42\x4d\xe4\x00\x00\x01\x73'
SWITCH_TO_NORMAL_MODE   = b'\x42\x4d\xe4\x00\x01\x01\x71'

# --- serial port
SERIAL_PORT = '/dev/ttyS0'
BAUDRATE = 9600

# --- timeout value
READ_TIMEOUT = 6

class PMSensor():

  __instance = None

  def instance():
    if PMSensor.__instance == None:
      PMSensor()
    return PMSensor.__instance

  def __init__(self, device=SERIAL_PORT, baudrate=BAUDRATE,
               pin_set=PIN.PM_SENSOR_SET, pin_reset=PIN.PM_SENSOR_RESET):
      if PMSensor.__instance == None:
        self._serial = None
        self._device = device
        self._baudrate = baudrate
        self._pin_set = pin_set
        self._pin_reset = pin_reset
        self.setup()
        PMSensor.__instance = self
      else:
        raise Exception('try to initialize multiple instance of a singleton')

  def setup(self):
    pi.set_mode(self._pin_set, PiGpio.OUTPUT)
    pi.set_mode(self._pin_reset, PiGpio.OUTPUT)

    try:
      self.serial_open()
      # self._run_mode = ''
      # self._read_mode = ''
    except Exception as e:
      print(e)
      self.serial_close()
    finally:
      pass

    self.wakeup()
    # self.reset()
    # self.set_passive_read_mode()

  def wakeup(self):
    pi.write(self._pin_set, PiGpio.LEVEL_HIGH)

  def reset(self):
    time.sleep(0.1)
    pi.write(self._pin_reset, PiGpio.LEVEL_LOW)
    time.sleep(0.1)
    pi.write(self._pin_reset, PiGpio.LEVEL_HIGH)

  def release_resource(self):
    self.serial_close()

  def set_active_read_mode(self):
    self._set_read_mode('active_mode')

  def set_passive_read_mode(self):
    self._set_read_mode('passive_mode')

  def passive_read(self):
    ret = None
    try:
      self._serial_write(PASSIVE_READ)
      ret = self._read()
    except Exception as e:
      print(e)
      self.serial_close()
    else:
      pass
    finally:
      return ret

  def read(self):
    return self._read()
    # ret = None
    # try:
    #   ret = self._read()
    # except Exception as e:
    #   print(e)
    #   self.serial_close()
    # else:
    #   pass
    # finally:
    #   return ret

  def serial_open(self):
    if self._serial is not None:
      pi.serial_close(self._serial)
    self._serial= pi.serial_open(self._device, self._baudrate, 0)

  def serial_close(self):
    if self._serial is not None:
      pi.serial_close(self._serial)
      self._serial = None

  # ------------ private ------------
  def _serial_read(self, count):
    b, d = pi.serial_read(self._serial, count)
    return b, d

  def _serial_write(self, data):
    pi.serial_write(self._serial, data)

  def _serial_flush_input(self):
    pass

  def _set_run_mode(self, mode):
    if mode == 'standby_mode':
      self._serial_write(SWITCH_TO_STANDBY_MODE)
    elif mode == 'normal_mode':
      self._serial_write(SWITCH_TO_NORMAL_MODE)
    else:
      pass
    # if mode != self._run_mode:
    #   if mode == 'standby_mode':
    #     self._serial_write(SWITCH_TO_STANDBY_MODE)
    #   elif mode == 'normal_mode':
    #     self._serial_write(SWITCH_TO_NORMAL_MODE)
    #   else:
    #     pass
    #   self._run_mode = mode

  def _set_read_mode(self, mode):
    if mode == 'active_mode':
      self._serial_write(SWITCH_TO_ACTIVE_MDOE)
    elif mode == 'passive_mode':
      self._serial_write(SWITCH_TO_PASSIVE_MODE)
    else:
      pass
    # if mode != self._read_mode:
    #   if mode == 'active_mode':
    #     self._serial_write(SWITCH_TO_ACTIVE_MDOE)
    #   elif mode == 'passive_mode':
    #     self._serial_write(SWITCH_TO_PASSIVE_MODE)
    #   else:
    #     pass
    #   self._read_mode = mode

  def _read(self):

    start_time = time.time()

    while True:
      # ------ check timeout
      elapsed = time.time() - start_time
      if elapsed > READ_TIMEOUT:
        raise PMFrameDataReadTimeoutError('PM sensor frame data read timeout: no valid frame packet found')

      # ------ check available bytes
      available_count = pi.serial_data_available(self._serial)
      # --- drop incomplete frame packet
      if available_count < PM_DATA_FRAME_LEN:
        count, data = self._serial_read(available_count)
        time.sleep(0.1)
        continue

      # ------ read and parse the intact frame packet
      else:
        # --- read all data
        count, data = self._serial_read(available_count)

        # --- head check
        if ( PM_DATA_FRAME_HEAD != data[:2] ):
          raise PMFrameDataCorruptError('PM sensor frame data corrupted: invalid head')

        # --- frame length and checksum value
        frame_length = int.from_bytes(data[2:4], byteorder='big')
        checksum = int.from_bytes(data[-2:], byteorder='big')

        # --- checksum check
        if ( sum(data[:-2]) != checksum ):
          raise PMFrameDataCorruptError('PM sensor frame data corrupted: checksum failed')

        # --- obtain pm data
        pm_data = PMSensorData(data[4:-2])
        # print('data length: ', frame_length)
        # print('checksum: ', checksum)
        # print(pm_data)
        break

    return pm_data
  # ---------------------------------

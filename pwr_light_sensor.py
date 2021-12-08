from i2c_switch_bus import I2CSwitchBus
import time


#--------------------------------------------------------------------
# ------------------ hardware setup
# --- I2C bus
# I2C_BUS_CHANNEL = 1
# i2c_bus = smbus2.SMBus(I2C_BUS_CHANNEL)
i2c_switch_bus = I2CSwitchBus.instance()
# --- TSL2561 sensor
TSL2561_3_ADDR              = 0x0439
TSL2561_RESPONSE_WAIT_TIME  = 0.05


#--------------------------------------------------------------------
# ------------------ TSL2561 command


#--------------------------------------------------------------------
# ------------------ constants
INVALID_VAL = -999


#--------------------------------------------------------------------
# ------------------ methods
_ON_THRESHOLD = 300
def read_tsl2561(addr):
  i2c_switch_bus.fulladdress_write_byte(addr, 0x00 | 0x80, 0x03)
  # time.sleep(TSL2561_RESPONSE_WAIT_TIME)
  i2c_switch_bus.fulladdress_write_byte(addr, 0x01 | 0x80, 0x02)
  time.sleep(TSL2561_RESPONSE_WAIT_TIME)

  data0 = i2c_switch_bus.fulladdress_read_block(addr,0x0C | 0x80, 2)
  data1 = i2c_switch_bus.fulladdress_read_block(addr,0x0E | 0x80, 2)

  # Convert the data
  ch0 = data0[1] * 256 + data0[0]
  ch1 = data1[1] * 256 + data1[0]

  visible = ch0 - ch1
  # print("Full Spectrum(IR + Visible): %d lux" %ch0)
  # print("Infrared Value: %d lux" %ch1)
  # print("Visible Value: %d lux" %(ch0 - ch1))

  return visible > _ON_THRESHOLD

def read_light():
  ison = read_tsl2561(TSL2561_3_ADDR)
  result_str = 'on' if ison else 'off'
  return ison, result_str

def to_str(on):
  return 'on' if on else 'off'

def ison():
  return read_tsl2561(TSL2561_3_ADDR)

def invalid_status():
  return INVALID_VAL

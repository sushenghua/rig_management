from i2c_switch_bus import I2CSwitchBus
import time


#--------------------------------------------------------------------
# ------------------ hardware setup
# --- I2C bus
# I2C_BUS_CHANNEL = 1
# i2c_bus = smbus2.SMBus(I2C_BUS_CHANNEL)
i2c_switch_bus = I2CSwitchBus()
# --- SHT3x sensor1
SHT3x_1_ADDR              = 0x0144
SHT3x_2_ADDR              = 0x0244
SHT3X_RESPONSE_WAIT_TIME  = 0.05


#--------------------------------------------------------------------
# ------------------ SHT3x command
# --- MSB bits
SHT3x_CLK_STRETCH_ENABLED       = 0x2C
SHT3x_CLK_STRETCH_DISABLED      = 0x24
# --- LSB bits
SHT3x_REPEATABILITY_HIGH_CSE    = 0x06 # CSE: CLK STRETCH ENABLED
SHT3x_REPEATABILITY_MEDIUM_CSE  = 0x0D
SHT3x_REPEATABILITY_LOW_CSE     = 0x10
SHT3x_REPEATABILITY_HIGH_CSD    = 0x00 # CSD: CLK STRETCH DISABLED
SHT3x_REPEATABILITY_MEDIUM_CSD  = 0x0B
SHT3x_REPEATABILITY_LOW_CSD     = 0x16


#--------------------------------------------------------------------
# ------------------ methods
def read_sht3x(addr, clk_stretch=False):
  if clk_stretch:
    i2c_switch_bus.fulladdress_write_block(addr, SHT3x_CLK_STRETCH_ENABLED, [SHT3x_REPEATABILITY_HIGH_CSE])
  else:
    i2c_switch_bus.fulladdress_write_block(addr, SHT3x_CLK_STRETCH_DISABLED, [SHT3x_REPEATABILITY_HIGH_CSD])
  time.sleep(SHT3X_RESPONSE_WAIT_TIME)
  # read data back from 0x00(00), 6 bytes
  # Temp MSB, Temp LSB, Temp CRC, Humididty MSB, Humidity LSB, Humidity CRC
  data = i2c_switch_bus.fulladdress_read_block(addr, 0x00, 6)
  # Convert the data
  temp = data[0] * 256 + data[1]
  cTemp = -45 + (175 * temp / 65535.0)
  fTemp = -49 + (315 * temp / 65535.0)
  humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
  result_str = ''.join(['temperature: %.2f C' % cTemp, \
                ' (%.2f F)' % fTemp, \
                ', humidity: %.2f%%' % humidity])
  return (cTemp, fTemp, humidity, result_str)

def read_upstream():
  return read_sht3x(SHT3x_1_ADDR)

def read_downstream():
  return read_sht3x(SHT3x_2_ADDR)

def read_all():
  _,_,_, up = read_sht3x(SHT3x_1_ADDR)
  _,_,_, down = read_sht3x(SHT3x_2_ADDR)
  return ''.join(['[up stream]  ', up, '\n',
                  '[down strem] ', down])
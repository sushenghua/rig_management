from pigpio_singleton import PiGpio
import pin_config as PIN
import smbus2
import time


#--------------------------------------------------------------------
# ------------------ hardware setup
# --- gpio
pi = PiGpio.instance().pi()
pi.set_mode(PIN.I2C_SWITCH_RESET, PiGpio.OUTPUT)

# --- I2C bus
I2C_BUS_CHANNEL = 1
i2c_bus = smbus2.SMBus(I2C_BUS_CHANNEL)

# --- I2C switch
# a switch(slave) chip(TCA9548A) for multiplexing switch, this chip has
# 8 channels, and these channels can be turned on by set corresponding
# bit to 1, or off by 0.
# eg. 0x01: first channel turned 'on', all others 'off'
#     0x14: third channle, fifth channel 'on', all rest 'off'
SWITCH_ADDRESS                = 0x70
SWITCH_CHANNEL_COUNT          = 8
SWITCH_SET_CHANNEL_WAIT_TIME  = 0.02


#--------------------------------------------------------------------
# ------------------ methods

class I2CSwitchBus():

  __instance = None

  def instance():
    if I2CSwitchBus.__instance == None:
      I2CSwitchBus()
    return I2CSwitchBus.__instance

  def __init__(self):
    if I2CSwitchBus.__instance == None:
      self.switch_reset()
      self._recent_channel_bitmask = 0x00
      i2c_bus.write_byte(SWITCH_ADDRESS, 0x00)
      time.sleep(SWITCH_SET_CHANNEL_WAIT_TIME)
      I2CSwitchBus.__instance = self
    else:
      raise Exception('try to initialize multiple instance of a singleton')

  # --- set bitwise channel
  def set_switch_bitwise_channel(self, channel_bitmask):
    newmask = channel_bitmask & 0xFF
    if (self._recent_channel_bitmask != newmask):
      self._recent_channel_bitmask = newmask
      i2c_bus.write_byte(SWITCH_ADDRESS, newmask)
      time.sleep(SWITCH_SET_CHANNEL_WAIT_TIME)

  # --- set change by number (0 - 7)
  def set_switch_channel(self, channel_number):
    if (0 <= channel_number < SWITCH_CHANNEL_COUNT):
      self.set_switch_bitwise_channel(0x01 << channel_number)

  # --- all channel off
  def set_switch_all_channel_off(self):
    self.set_switch_bitwise_channel(0x00)

  # --- standard address (only device address) read, write
  def stdaddress_read_byte(self, addr, register):
    return i2c_bus.read_byte_data(addr, register)

  def stdaddress_read_block(self, addr, register, length):
    return i2c_bus.read_i2c_block_data(addr, register, length)

  def stdaddress_write_byte(self, addr, register, value):
    i2c_bus.write_byte_data(addr, register, value)

  def stdaddress_write_block(self, addr, register, block):
    i2c_bus.write_i2c_block_data(addr, register, block)

  # --- full address (channel mask + device address) read, write
  def fulladdress_read_byte(self, fulladdress, register):
    self.set_switch_bitwise_channel(fulladdress >> 8)
    return i2c_bus.read_byte_data(fulladdress & 0xFF, register)

  def fulladdress_read_block(self, fulladdress, register, length):
    self.set_switch_bitwise_channel(fulladdress >> 8)
    return i2c_bus.read_i2c_block_data(fulladdress & 0xFF, register, length)

  def fulladdress_write_byte(self, fulladdress, register, value):
    self.set_switch_bitwise_channel(fulladdress >> 8)
    i2c_bus.write_byte_data(fulladdress & 0xFF, register, value)

  def fulladdress_write_block(self, fulladdress, register, block):
    self.set_switch_bitwise_channel(fulladdress >> 8)
    i2c_bus.write_i2c_block_data(fulladdress & 0xFF, register, block)

  def fulladdress_byte_process_call(self, fulladdress, register, value):
    self.set_switch_bitwise_channel(fulladdress >> 8)
    return i2c_bus.process_call(fulladdress & 0xFF, register, value)

  def fulladdress_block_process_call(self, fulladdress, register, block):
    self.set_switch_bitwise_channel(fulladdress >> 8)
    return i2c_bus.block_process_call(fulladdress & 0xFF, register, block)

  # --- reset switch
  def switch_reset(self):
    pi.write(PIN.I2C_SWITCH_RESET, PiGpio.LEVEL_LOW)
    time.sleep(0.1)
    pi.write(PIN.I2C_SWITCH_RESET, PiGpio.LEVEL_HIGH)

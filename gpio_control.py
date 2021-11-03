from pigpio_singleton import PiGpio
import pin_config as PIN
import time


#--------------------------------------------------------------------
# ------------------ hardware setup
# --- gpio
pi = PiGpio.instance().pi()
pi.set_mode(PIN.POWER_STATUS, PiGpio.INPUT)
pi.set_mode(PIN.USB_PLUG, PiGpio.OUTPUT)
pi.set_mode(PIN.POWER_BUTTON, PiGpio.OUTPUT)
pi.set_mode(PIN.PM_SENSOR_SET, PiGpio.OUTPUT)
pi.set_mode(PIN.PM_SENSOR_RESET, PiGpio.OUTPUT)


#--------------------------------------------------------------------
# ------------------ methods
def set_usb_enabled(enabled:bool):
  level = PiGpio.LEVEL_HIGH if enabled else PiGpio.LEVEL_LOW
  pi.write(PIN.USB_PLUG, level)

def read_power_status():
    ison = pi.read(PIN.POWER_STATUS)
    result_str = 'power: %s'%('on' if ison else 'off')
    return ison, result_str

def power_toggle():
  pi.write(PIN.POWER_BUTTON, PiGpio.LEVEL_HIGH)
  time.sleep(0.2)
  pi.write(PIN.POWER_BUTTON, PiGpio.LEVEL_LOW)

def power_longpress():
  pi.write(PIN.POWER_BUTTON, PiGpio.LEVEL_HIGH)
  time.sleep(6)
  pi.write(PIN.POWER_BUTTON, PiGpio.LEVEL_LOW)

def pm_sensor_set_wakeup(wakeup:bool):
  pi.write(PIN.PM_SENSOR_SET, wakeup)

def pm_sensor_reset():
  pi.write(PIN.PM_SENSOR_RESET, PiGpio.LEVEL_LOW)
  time.sleep(0.1)
  pi.write(PIN.PM_SENSOR_RESET, PiGpio.LEVEL_HIGH)

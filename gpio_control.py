from pigpio_singleton import PiGpio
import pin_config as PIN
import time


#--------------------------------------------------------------------
# ------------------ hardware setup
# --- gpio
pi = PiGpio.instance().pi()
pi.set_mode(PIN.USB_PLUG, PiGpio.OUTPUT)
pi.set_mode(PIN.POWER_BUTTON, PiGpio.OUTPUT)
pi.set_mode(PIN.PM_SENSOR_SET, PiGpio.OUTPUT)
pi.set_mode(PIN.PM_SENSOR_RESET, PiGpio.OUTPUT)
pi.set_mode(PIN.PWM1_CHANNEL1, PiGpio.OUTPUT)
pi.set_mode(PIN.PWM1_CHANNEL2, PiGpio.OUTPUT)

# pi.set_mode(PIN.PWM1_CHANNEL, PiGpio.INPUT)
# pi.set_pull_up_down(PIN.PWM1_CHANNEL, PiGpio.PULLDOWN)


#--------------------------------------------------------------------
# ------------------ methods
def set_usb_enabled(enabled:bool):
  level = PiGpio.LEVEL_HIGH if enabled else PiGpio.LEVEL_LOW
  pi.write(PIN.USB_PLUG, level)

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

def _set_pwm(channel_pin, dutycycle, frequency=23400):
  dutycycle = 0 if dutycycle < 0 else 1.0 if dutycycle > 1.0 else dutycycle
  pi.set_PWM_frequency(channel_pin, frequency)
  pi.set_PWM_dutycycle(channel_pin, 255*dutycycle)

def set_pwm1(dutycycle, frequency=23400):
  _set_pwm(PIN.PWM1_CHANNEL1, dutycycle, frequency)

def set_pwm2(dutycycle, frequency=23400):
  _set_pwm(PIN.PWM1_CHANNEL2, dutycycle, frequency)
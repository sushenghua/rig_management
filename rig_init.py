#!/usr/bin/env python3

import gpio_control as control
import pwr_light_sensor as pwrlight
import time


# --- wait time
WAIT_INTERVAL = 0.3

# --- init pm sensor
control.pm_sensor_set_wakeup(True)
time.sleep(WAIT_INTERVAL)
control.pm_sensor_reset()
time.sleep(WAIT_INTERVAL)

# --- init fan pwm
PWM_INIT_PERCENT = 32
control.set_pwm1(PWM_INIT_PERCENT/100.0)

# --- read ps status: since initial read return invalid result
pwrlight.read_light()

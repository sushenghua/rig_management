
import pigpio

class PiGpio:

  LEVEL_LOW = 0
  LEVEL_HIGH = 1
  INPUT = pigpio.INPUT
  OUTPUT = pigpio.OUTPUT

  __instance = None

  def instance():
    if PiGpio.__instance == None:
      PiGpio()
    return PiGpio.__instance

  def __init__(self):
    if PiGpio.__instance == None:
      self._pi = pigpio.pi()
      PiGpio.__instance = self
    else:
      raise Exception('try to initialize multiple instance of a singleton')

  def pi(self):
    return self._pi

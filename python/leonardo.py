
"""
Demo the LattePanda on-board Arduino I/O capabilities with Python
"""

import logging
import math
import sys
import time
import tkinter

from pyfirmata import Arduino, util

logging.basicConfig(
	filemode='a+', 
	filename='logfile.txt', 
	level=logging.INFO, 
	format='%(asctime)s (%(levelname)s,%(module)s,%(lineno)d) %(message)s',
	)
logger = logging.getLogger(__file__)

UI_SCREEN = "leonardo.ui"
LEO_COMM_PORT = "COM3"
LOOP_DELAY_S = 0.091
REPORT_INTERVAL_S = 600


class Leonardo:

	def __init__(self, port=None):
		self.T0, self.T1, self.LDR, self.PIR = None, None, None, None
		self.LDR_TC, self.LDR_BR, self.LDR_BL = None, None, None
		self.pos_x = None

		self.t0 = time.time()
		
		self.port = port or LEO_COMM_PORT
		self.leonardo = Arduino(self.port)

		self.it = util.Iterator(self.leonardo)
		self.it.start()

		self.pin_t0 = self.leonardo.get_pin("a:0:i")
		self.pin_t1 = self.leonardo.get_pin("a:1:i")
		self.pin_ldr = self.leonardo.get_pin("a:2:i")
		self.pin_pir = self.leonardo.get_pin("d:9:i")
		self.pin_led = self.leonardo.get_pin("d:13:o")
		self.pir_counter = 0
		self.pir_previous = None
		self.pin_ldr_tc = self.leonardo.get_pin("a:3:i")
		self.pin_ldr_br = self.leonardo.get_pin("a:4:i")
		self.pin_ldr_bl = self.leonardo.get_pin("a:5:i")
		
		for nm in ("t0 t1 ldr pir ldr_tc ldr_br ldr_bl".split()):
			item = getattr(self, "pin_"+nm)
			item.enable_reporting()
			item.read()        # first read is usually None
		
		self.read()

	def __repr__(self):
		names = "port T0 T1 LDR pir_counter PIR LDR_TC LDR_BR LDR_BL".split()
		a = [f"{getattr(self, nm)}=\"{obj}\"" for nm in names]
		s = "Leonardo(" + ",".join(a) + ")"
		return s

	def read(self):
		self.timestamp = time.time() - self.t0
		self.T0 = self.read_temperature(self.pin_t0)
		self.T1 = self.read_temperature(self.pin_t1)
		self.LDR = self.read_raw(self.pin_ldr)
		self.pir_previous = self.PIR
		self.PIR = self.read_raw(self.pin_pir)
		if self.PIR and not self.pir_previous:
			self.pir_counter += 1
			logger.debug(f"PIR motion detected {self.pir_counter}")
			self.pin_led.write(1)
		elif not self.PIR and self.pir_previous:
			logger.debug("PIR reset")
			self.pin_led.write(0)
		self.LDR_TC = self.read_raw(self.pin_ldr_tc)
		self.LDR_BR = self.read_raw(self.pin_ldr_br)
		self.LDR_BL = self.read_raw(self.pin_ldr_bl)
		if None not in (self.LDR_BR, self.LDR_BL):
			self.pos_x = (self.LDR_BR - self.LDR_BL) / (self.LDR_BR + self.LDR_BL)
		self.t0 = time.time()

	def read_raw(self, pin, retries=5):
		"""read signal from pyfirmata pin"""
		signal = None
		count = 0
		while signal is None and count < retries:
			count += 1
			signal = pin.read()
		if signal is None:
			logger.debug(f"port {self.port}: no signal from {pin} after {retries} retries")
		return signal

	def read_temperature(self, pin):
		"""read temperature for thermistor"""
		C_KELVIN_OFFSET = 273.15
		OHM_REF = 10000
		
		# https://www.skyeinstruments.com/wp-content/uploads/Steinhart-Hart-Eqn-for-10k-Thermistors.pdf
		A = 0.001125308852122
		B = 0.000234711863267
		C = 0.000000085663516
		
		signal = self.read_raw(pin)
		if signal is None:
			return
		value = OHM_REF / (1/signal - 1)            # resistance, ohms
		
		# use Steinhart-Hart approximation to get temperature
		value = math.log(value)
		value = 1/(A + B*value + C*value*value*value) - C_KELVIN_OFFSET
		return value


def sec2timestring(secs):
	w = int(secs/(7*24*60*60))
	d = int(secs/(24*60*60)) % 7
	h = int(secs/(60*60)) % 24
	m = int(secs/60) % 60
	s = secs % 60
	text = []
	if w > 0:
		text.append(f"{w}w")
	if d > 0:
		text.append(f"{d}d")
	if h > 0:
		text.append(f"{h}h")
	if m > 0:
		text.append(f"{m}m")
	if s > 0:
		text.append("%.1fs" % s)
	return " ".join(text)


def main():
	win = tkinter.Tk()
	win.title("LattePanda sensor demo")
	
	# build form
	config = """
	T0          \t  NTC 10k Thermistor 1, C
	T1          \t  NTC 10k Thermistor 2, C
	LDR         \t  LDR photoresistor
	PIR         \t  PIR motion sensor
	pir_counter \t  motion events counted
	LDR_TC      \t  photocell, top-center
	LDR_BR      \t  photocell, bottom-right
	LDR_BL      \t  photocell, bottom-left
	pos_x       \t  position, X-axis
	timestamp   \t  update time, s
	time        \t  system Up time
	"""
	logger.info("#"*40)
	logger.info(f"Starting {__file__}")
	row = 0
	widgets = {}
	for line in config.strip().splitlines():
		key, text = line.strip().split("\t")
		lbl = tkinter.Label(win, text=text)
		lbl.grid(row=row, column=0)
		v = tkinter.StringVar(win)
		lbl = tkinter.Label(win, textvariable=v)
		lbl.grid(row=row, column=1)
		widgets[key.strip()] = v
		row += 1
	time_widget = widgets["time"]
	del widgets["time"]
	
	logger.info("Connecting with Arduino ...")
	leo = Leonardo()
	logger.info(f"Connected port {leo.port}!")

	# win.mainloop()
	t0 = time.time()
	report = t0  # start periodic reporting
	while True:
		try:
			leo.read()
		except Exception as e:
			logger.exception("Exception raised when leo={leo}\n{e}")
		elapsed = sec2timestring(time.time() - t0)
		time_widget.set(elapsed)
		msg = []
		for key, widget in widgets.items():
			v = getattr(leo, key)
			if key in ("T0", "T1", "timestamp", "pos_x") and v is not None:
				try:
					v = "%.3f" % v
				except Exception as e:
					logger.exception("Exception raised when leo={leo}\n{e}")
			try:
				widget.set(str(v))
				msg.append(f"{key}={v}")
			except Exception as e:
				logger.exception("Exception raised when leo={leo}\n{e}")
		msg.append(f"elapsed={elapsed}")
		if time.time() > report:
			report += REPORT_INTERVAL_S
			logger.info(" ".join(msg))
		win.update_idletasks()
		win.update()
		time.sleep(LOOP_DELAY_S)

if __name__ == '__main__':
	main()

import sys
import tkinter		# can't import PyQt5,QtWidgets: ImportError: DLL load failed: The specified module could not be found.

import math
import time
from pyfirmata import Arduino, util


UI_SCREEN = "leonardo.ui"
LEO_COMM_PORT = "COM5"
LOOP_DELAY_S = 0.1


class Leonardo:

	def __init__(self, port=None):
		self.T0, self.T1, self.LDR, self.PIR = None, None, None, None
		self.t0 = time.time()
		
		self.port = port or LEO_COMM_PORT
		self.leonardo = Arduino(self.port)

		self.it = util.Iterator(self.leonardo)
		self.it.start()

		self.pin_t0 = self.leonardo.get_pin("a:0:i")
		self.pin_t1 = self.leonardo.get_pin("a:1:i")
		self.pin_ldr = self.leonardo.get_pin("a:2:i")
		self.pin_pir = self.leonardo.get_pin("d:9:i")
		
		for item in (self.pin_t0, self.pin_t1, self.pin_ldr, self.pin_pir):
			item.enable_reporting()
			item.read()        # first read is usually None
		
		self.read()

	def read(self):
		self.timestamp = time.time() - self.t0
		self.T0 = self.read_temperature(self.pin_t0)
		self.T1 = self.read_temperature(self.pin_t1)
		self.LDR = self.read_raw(self.pin_ldr)
		self.PIR = self.read_raw(self.pin_pir)
		# print(
		# 	f"{self.timestamp}",
		# 	f" T0={self.T0}",
		# 	f" T1={self.T1}",
		# 	f" LDR={self.LDR}",
		# 	f" PIR={self.PIR}",
		# )
		self.t0 = time.time()

	def read_raw(self, pin, retries=5):
		"""read signal from pyfirmata pin"""
		signal = None
		count = 0
		while signal is None and count < retries:
			count += 1
			signal = pin.read()
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


def main():
	win = tkinter.Tk()
	win.title("LattePanda sensor demo")
	
	# build form
	config = """
	T0         \t  NTC 10k Thermistor 1, C
	T1         \t  NTC 10k Thermistor 2, C
	LDR        \t  LDR photoresistor
	PIR        \t  PIR motion sensor
	timestamp  \t  update time, s
	time       \t  elapsed system time
	"""
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
	
	print("Connecting with Arduino ...")
	leo = Leonardo()
	print("Connected!")

	# win.mainloop()
	t0 = time.time()
	while True:
		leo.read()
		elapsed = time.time() - t0
		time_widget.set("%.3f" % elapsed)
		for key, widget in widgets.items():
			v = getattr(leo, key)
			if key in ("T0", "T1", "timestamp") and v is not None:
				v = "%.3f" % v
			widget.set(str(v))
		win.update_idletasks()
		win.update()
		time.sleep(LOOP_DELAY_S)

if __name__ == '__main__':
	main()

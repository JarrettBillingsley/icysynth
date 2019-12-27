from nmigen import *
from nmigen.build import Platform

from uart import *
from signals import *

# --------------------------------------------------------------------------------------------------
# Serial UART Command interface
# --------------------------------------------------------------------------------------------------

# much of this code taken from nmigen-examples/receive-uart.py

class UartCmd(Elaboratable):
	def __init__(self, num_channels, bits_over_8, baudrate, clk_freq):
		self.num_channels = num_channels
		self.baudrate     = baudrate
		self.clk_freq     = clk_freq
		self.divisor      = int(self.clk_freq // self.baudrate)

		# -------------------------------------
		# Inputs

		self.rx = Signal(reset = 1)

		# -------------------------------------
		# Outputs

		self.o = CommandOutput(num_channels, bits_over_8)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		self.uart = UARTRx(divisor = self.divisor)
		m.submodules.uart = self.uart

		# -------------------------------------
		# Internal State

		# This stuff is just temporary.
		chan_enable = Signal(self.num_channels, reset = ~0)
		noise_period = Signal(8)
		noise_period.reset = 1
		noise_mode = Signal(1)

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			self.uart.rx_pin.eq(self.rx),
			self.o.sampler_i.chan_enable.eq(chan_enable),
			self.o.noise_i.period.eq(noise_period),
			self.o.noise_i.mode.eq(noise_mode),
		]

		# -------------------------------------
		# Sequential Logic

		ready = self.uart.rx_rdy
		data = self.uart.rx_data

		with m.If(ready):
			with m.Switch(data):
				for i in range(self.num_channels):
					with m.Case(ord('1') + i):
						m.d.sync += chan_enable.eq(chan_enable ^ 1 << i)
						m.d.sync += self.o.sampler_i.chan_enable_we.eq(1)
				with m.Case(ord('a')):
					m.d.sync += noise_period.eq(noise_period + 1)
					m.d.sync += self.o.noise_we.period.eq(1)
				with m.Case(ord('z')):
					m.d.sync += noise_period.eq(noise_period - 1)
					m.d.sync += self.o.noise_we.period.eq(1)
				with m.Case(ord('w')):
					m.d.sync += noise_mode.eq(~noise_mode)
					m.d.sync += self.o.noise_we.mode.eq(1)


		return m

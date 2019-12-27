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

		chan_enable = Signal(self.num_channels, reset = ~0)

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			self.uart.rx_pin.eq(self.rx),
			self.o.sampler_i.chan_enable.eq(chan_enable),
		]

		# -------------------------------------
		# Sequential Logic

		ZERO = ord('0')
		ONE = ord('1')
		ready = self.uart.rx_rdy
		data = self.uart.rx_data

		with m.FSM(name = 'cmd_fsm') as fsm:
			with m.State('IDLE'):
				with m.If(ready):
					with m.If((data > ZERO) & (data <= (ZERO + self.num_channels))):
						w = Signal(range(self.num_channels)).shape().width
						m.d.sync += [
							chan_enable.eq(chan_enable ^ (1 << (data - ONE)[:w])),
							self.o.sampler_i.chan_enable_we.eq(1)
						]

						m.next = 'TICKLE'

			with m.State('TICKLE'):
				m.d.sync += [
					self.o.sampler_i.chan_enable_we.eq(0),
				]

				m.next = 'IDLE'

		return m

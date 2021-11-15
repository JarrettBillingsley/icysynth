from nmigen import *
from nmigen.build import Platform

from uart import *
from signals import *

# --------------------------------------------------------------------------------------------------
# Serial UART Command interface
# --------------------------------------------------------------------------------------------------

# much of this code taken from nmigen-examples/receive-uart.py

class UartCmd(Elaboratable):
	def __init__(self, baudrate, clk_freq):
		self.baudrate     = baudrate
		self.clk_freq     = clk_freq
		self.divisor      = int(self.clk_freq // self.baudrate)

		# -------------------------------------
		# Inputs

		# From host
		self.rx = Signal(reset = 1)

		# From Cmd
		self.processing = Signal()

		# -------------------------------------
		# Outputs

		# To host
		self.cts = Signal(reset = 1)

		# To Cmd
		self.o = CommandInput()

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		m.submodules.uart_rx = self.uart = UARTRx(divisor = self.divisor)

		# -------------------------------------
		# Internal State

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			self.uart.rx_pin.eq(self.rx),
		]

		# -------------------------------------
		# Sequential Logic

		ready = self.uart.rx_rdy
		data = self.uart.rx_data

		with m.FSM(name = 'uart_fsm') as fsm:
			with m.State('WAIT_OP'):
				with m.If(ready):
					m.d.sync += self.o.cmd_op.eq(data)
					m.next = 'WAIT_ARG0'
			with m.State('WAIT_ARG0'):
				with m.If(ready):
					m.d.sync += self.o.cmd_arg_0.eq(data)
					m.next = 'WAIT_ARG1'
			with m.State('WAIT_ARG1'):
				with m.If(ready):
					m.d.sync += self.o.cmd_arg_1.eq(data)
					m.next = 'WAIT_ARG2'
			with m.State('WAIT_ARG2'):
				with m.If(ready):
					m.d.sync += self.o.cmd_arg_2.eq(data)
					m.d.sync += self.o.cmd_ready.eq(1)
					m.d.sync += self.cts.eq(0)
					m.next = 'SENDING'
			with m.State('SENDING'):
				with m.If(~self.processing):
					m.d.sync += self.o.cmd_ready.eq(0)
					m.d.sync += self.cts.eq(1)
					m.next = 'WAIT_OP'

		return m
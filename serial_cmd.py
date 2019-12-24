from nmigen import *
from nmigen.build import Platform

from uart import *
from signals import *

# --------------------------------------------------------------------------------------------------
# Serial UART Command interface
# --------------------------------------------------------------------------------------------------

# much of this code taken from nmigen-examples receive-uart.py

class OneShot(Elaboratable):
	def __init__(self, duration):
		self.duration = duration
		self.trg = Signal()
		self.out = Signal()

	def elaborate(self, platform):
		counter = Signal(range(-1, self.duration))
		m = Module()
		with m.If(self.trg):
			m.d.sync += [
				counter.eq(self.duration - 2),
				self.out.eq(True),
			]
		with m.Elif(counter[-1]):
			m.d.sync += self.out.eq(False)
		with m.Else():
			m.d.sync += counter.eq(counter - 1)
		return m

class UartCmd(Elaboratable):
	def __init__(self, num_channels, baudrate, clk_freq):
		self.baudrate = baudrate
		self.clk_freq = clk_freq

		# -------------------------------------
		# Inputs

		self.rx = Signal(reset = 1)

		# -------------------------------------
		# Outputs

		self.o             = CommandOutput(num_channels)
		self.o_recv_status = Signal()
		self.o_err_status  = Signal()

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		uart_divisor    = int(self.clk_freq // self.baudrate)
		status_duration = int(0.1 * self.clk_freq)

		uart_rx         = UARTRx(divisor = uart_divisor)
		recv_status     = OneShot(duration = status_duration)
		err_status      = OneShot(duration = status_duration)

		m.submodules.uart_rx     = uart_rx
		m.submodules.recv_status = recv_status
		m.submodules.err_status  = err_status

		m.d.comb += [
			uart_rx.rx_pin    .eq(self.rx        ),
			recv_status.trg   .eq(uart_rx.rx_rdy ),
			err_status.trg    .eq(uart_rx.rx_err ),
			self.o_recv_status.eq(recv_status.out),
			self.o_err_status .eq(err_status.out),
		]

		# with m.If(uart_rx.rx_rdy):
			# m.d.sync += digit_leds[i].eq(uart_rx.rx_data == ord('1'))
		return m

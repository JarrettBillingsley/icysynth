from nmigen import *
from nmigen.build import Platform

from uart import *
from signals import *

# --------------------------------------------------------------------------------------------------
# Serial UART Command interface
# --------------------------------------------------------------------------------------------------

# much of this code taken from nmigen-examples receive-uart.py

class OneShot(Elaboratable):
	def __init__(self, duration, name):
		self.duration = duration
		self.trg = Signal(name=name+"_trg")
		self.out = Signal(name=name+"_out")

	def elaborate(self, platform):
		counter = Signal(range(self.duration + 1))
		m = Module()
		with m.If(self.trg):
			m.d.sync += [
				counter.eq(self.duration),
				self.out.eq(True),
			]
		with m.Elif(counter == 0):
			m.d.sync += self.out.eq(False)
		with m.Else():
			m.d.sync += counter.eq(counter - 1)
		return m

class UartCmd(Elaboratable):
	def __init__(self, num_channels, baudrate, clk_freq):
		self.num_channels = num_channels
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
		recv_status     = OneShot(duration = status_duration, name="recv")
		err_status      = OneShot(duration = status_duration, name="err")

		self.uart_rx = uart_rx
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

		chan_enable = Signal(self.num_channels, reset = (1 << self.num_channels) - 1)

		m.d.comb += self.o.mixer_i.inputs.chan_enable.eq(chan_enable)

		ZERO = ord('0')
		ONE = ord('1')
		ready = uart_rx.rx_rdy
		data = uart_rx.rx_data

		with m.FSM(name = 'cmd_fsm') as fsm:
			with m.State('IDLE'):
				with m.If(ready):
					with m.If((data > ZERO) & (data <= (ZERO + self.num_channels))):
						m.d.sync += [
							chan_enable.eq(chan_enable ^ (1 << (data - ONE))),
							self.o.mixer_i.we.chan_enable.eq(1)
						]

						m.next = 'TICKLE'

			with m.State('TICKLE'):
				m.d.sync += [
					self.o.mixer_i.we.chan_enable.eq(0),
					self.o.mixer_i.commit.eq(1),
				]

				m.next = 'BLOOP'

			with m.State('BLOOP'):
				m.d.sync += self.o.mixer_i.commit.eq(0)
				m.next = 'IDLE'

		return m

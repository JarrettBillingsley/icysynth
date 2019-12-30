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

		self.rx   = Signal(reset = 1)
		self.busy = Signal()

		# -------------------------------------
		# Outputs

		self.o = CommandOutput(num_channels, bits_over_8)
		self.cts = Signal(reset = 1)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		m.submodules.uart = self.uart = UARTRx(divisor = self.divisor)

		# -------------------------------------
		# Internal State

		# This stuff is just temporary.
		# chan_enable  = Signal(self.num_channels, reset = ~0)
		# noise_period = Signal(8, reset = 1)
		# noise_mode   = Signal(1)
		# noise_on     = Signal(1, reset = 1)

		self.cmd_op   = Signal(8)
		self.cmd_args = Array([Signal(8, name=f'cmd_arg_{i}') for i in range(3)])
		self.cmd_chan = self.cmd_args[0][4:7]

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			self.uart.rx_pin.eq(self.rx),
			# self.o.sampler_i.chan_enable.eq(chan_enable),
			# self.o.noise_i.period.eq(noise_period),
			# self.o.noise_i.mode.eq(noise_mode),
			# self.o.noise_i.vol.eq(Repl(noise_on, VOL_BITS))
		]

		# -------------------------------------
		# Sequential Logic

		ready = self.uart.rx_rdy
		data = self.uart.rx_data

		m.d.sync += self.o.sampler_i.chan_enable_we.eq(0)
		m.d.sync += self.o.sampler_i.chan_we.phase.eq(0)
		m.d.sync += self.o.sampler_i.chan_we.rate.eq(0)
		m.d.sync += self.o.sampler_i.chan_we.sample.eq(0)
		m.d.sync += self.o.sampler_i.chan_we.vol.eq(0)
		m.d.sync += self.o.noise_we.period.eq(0)
		m.d.sync += self.o.noise_we.mode.eq(0)
		m.d.sync += self.o.noise_we.vol.eq(0)
		m.d.sync += self.o.mixer_we.mix_shift.eq(0)

		with m.FSM(name = 'cmd_fsm') as fsm:
			with m.State('WAIT_OP'):   self.wait_op (m, ready, data)
			with m.State('WAIT_ARG0'): self.wait_arg(m, ready, data, 0)
			with m.State('WAIT_ARG1'): self.wait_arg(m, ready, data, 1)
			with m.State('WAIT_ARG2'): self.wait_arg(m, ready, data, 2)
			with m.State('00_SILENCE'):      # 00: (_, _, _) silence
				m.d.sync += self.o.sampler_i.chan_enable.eq(0)
				m.d.sync += self.o.sampler_i.chan_enable_we.eq(1)
				m.d.sync += self.o.noise_i.vol.eq(0)
				m.d.sync += self.o.noise_we.vol.eq(1)
				self.back_to_wait(m)
			with m.State('01_UNUSED'):       # 01: (_, _, _) (unused, commit)
				self.back_to_wait(m)
			with m.State('02_MIX_SHIFT'):    # 02: (s, _, _) mix shift
				m.d.sync += self.o.mixer_i.mix_shift.eq(self.cmd_args[0])
				m.d.sync += self.o.mixer_we.mix_shift.eq(1)
				self.back_to_wait(m)
			with m.State('03_NOISE_VOLUME'): # 03: (v, _, _) noise vol
				m.d.sync += self.o.noise_i.vol.eq(self.cmd_args[0])
				m.d.sync += self.o.noise_we.vol.eq(1)
				self.back_to_wait(m)
			with m.State('04_NOISE_PERIOD'): # 04: (p, m, _) noise period/mode
				m.d.sync += self.o.noise_i.period.eq(self.cmd_args[0])
				m.d.sync += self.o.noise_we.period.eq(1)
				m.d.sync += self.o.noise_i.mode.eq(self.cmd_args[1])
				m.d.sync += self.o.noise_we.mode.eq(1)
				self.back_to_wait(m)
			with m.State('05_SAMPLE_2'):     # 05: (a, v, _) set sample byte?
				# TODO
				self.back_to_wait(m)
			with m.State('06_SAMPLE_4'):     # 06: (a, v, w) set sample bytes?
				# TODO
				self.back_to_wait(m)
			with m.State('07_CHAN_ENABLE'):  # 07: (m, _, _) channel enable mask
				m.d.sync += self.o.sampler_i.chan_enable.eq(self.cmd_args[0])
				m.d.sync += self.o.sampler_i.chan_enable_we.eq(1)
				self.back_to_wait(m)
			with m.State('X0_RATE'):         # n0: (l, m, h) rate
				# TODO
				self.back_to_wait(m)
			with m.State('X1_RESET_PHASE'):  # n1: (_, _, _) reset phase
				# TODO
				self.back_to_wait(m)
			with m.State('X2_RATE_RESET'):   # n2: (l, m, h) rate + reset phase
				# TODO
				self.back_to_wait(m)
			with m.State('X3_SAMPLE'):       # n3: (s, l, _) sample
				# TODO
				self.back_to_wait(m)
			with m.State('X4_VOLUME'):       # n4: (v, _, _) volume
				# TODO
				self.back_to_wait(m)

		return m

	# TODO: deal with self.busy

	def wait_op(self, m, ready, data):
		with m.If(ready):
			m.d.sync += self.cmd_op.eq(data)
			m.next = 'WAIT_ARG0'

	def wait_arg(self, m, ready, data, i):
		with m.If(ready):
			m.d.sync += self.cmd_args[i].eq(data)
			if i < 2:
				m.next = f'WAIT_ARG{i+1}'
			else:
				self.dispatch(m)

	def dispatch(self, m):
		m.d.sync += self.cts.eq(0)

		with m.Switch(self.cmd_op):
 			with m.Case(0x00):       m.next = '00_SILENCE'
 			with m.Case(0x01):       m.next = '01_UNUSED'
 			with m.Case(0x02):       m.next = '02_MIX_SHIFT'
 			with m.Case(0x03):       m.next = '03_NOISE_VOLUME'
 			with m.Case(0x04):       m.next = '04_NOISE_PERIOD'
 			with m.Case(0x05):       m.next = '05_SAMPLE_2'
 			with m.Case(0x06):       m.next = '06_SAMPLE_4'
 			with m.Case(0x07):       m.next = '07_CHAN_ENABLE'
 			with m.Case('1---0000'): m.next = 'X0_RATE'
 			with m.Case('1---0001'): m.next = 'X1_RESET_PHASE'
 			with m.Case('1---0010'): m.next = 'X2_RATE_RESET'
 			with m.Case('1---0011'): m.next = 'X3_SAMPLE'
 			with m.Case('1---0100'): m.next = 'X4_VOLUME'
 			with m.Default():        self.back_to_wait(m)

	def back_to_wait(self, m):
		m.next = 'WAIT_OP'
		m.d.sync += self.cts.eq(1)

	def silly(self, m):
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
				with m.Case(ord('0')):
					m.d.sync += noise_on.eq(~noise_on)
					m.d.sync += self.o.noise_we.vol.eq(1)
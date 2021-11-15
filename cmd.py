from nmigen import *
from nmigen.build import Platform

from signals import *

# --------------------------------------------------------------------------------------------------
# Abstract command interface
# --------------------------------------------------------------------------------------------------

class Cmd(Elaboratable):
	def __init__(self, num_channels, bits_over_8):

		# -------------------------------------
		# Inputs

		# From some concrete physical interface
		self.i = CommandInput()

		# From the sampler
		self.busy = Signal()

		# -------------------------------------
		# Outputs

		self.o = CommandOutput(num_channels, bits_over_8)
		self.processing = Signal()

	def elaborate(self, platform):
		m = Module()

		# -------------------------------------
		# Internal State


		# -------------------------------------
		# Combinational Logic

		cmd_chan = self.i.cmd_op[4:7]
		rate = Cat(self.i.cmd_arg_0, self.i.cmd_arg_1, self.i.cmd_arg_2)

		m.d.comb += [
			self.o.sampler_i.chan_select.eq(cmd_chan),
			self.o.sampler_i.chan_i.rate.eq(rate),
			self.o.sampler_i.chan_i.start.eq(self.i.cmd_arg_0),
			self.o.sampler_i.chan_i.length.eq(self.i.cmd_arg_1),
			self.o.sampler_i.chan_i.vol.eq(self.i.cmd_arg_0),
			self.o.mixer_i.mix_shift.eq(self.i.cmd_arg_0),
			self.o.noise_i.vol.eq(self.i.cmd_arg_0),
			self.o.noise_i.period.eq(self.i.cmd_arg_0),
			self.o.sampler_i.chan_enable.eq(self.i.cmd_arg_0),
			self.o.noise_i.mode.eq(self.i.cmd_arg_1),
		]

		# -------------------------------------
		# Sequential Logic

		m.d.sync += self.o.sampler_i.chan_enable_we.eq(0)
		m.d.sync += self.o.sampler_i.chan_we.phase.eq(0)
		m.d.sync += self.o.sampler_i.chan_we.rate.eq(0)
		m.d.sync += self.o.sampler_i.chan_we.sample.eq(0)
		m.d.sync += self.o.sampler_i.chan_we.vol.eq(0)
		m.d.sync += self.o.noise_we.period.eq(0)
		m.d.sync += self.o.noise_we.mode.eq(0)
		m.d.sync += self.o.noise_we.vol.eq(0)
		m.d.sync += self.o.mixer_we.mix_shift.eq(0)

		# TODO: deal with self.busy

		with m.FSM(name = 'cmd_fsm') as fsm:
			with m.State('WAIT'):
				with m.If(self.i.cmd_ready):
					self.dispatch(m)
			with m.State('00_SILENCE'):      # 00: (_, _, _) silence
				m.d.comb += self.o.sampler_i.chan_enable.eq(0)
				m.d.sync += self.o.sampler_i.chan_enable_we.eq(1)
				m.d.comb += self.o.noise_i.vol.eq(0)
				m.d.sync += self.o.noise_we.vol.eq(1)
				m.next = 'WAIT'
			with m.State('01_UNUSED'):       # 01: (_, _, _) (unused, commit)
				m.next = 'WAIT'
			with m.State('02_MIX_SHIFT'):    # 02: (s, _, _) mix shift
				m.d.sync += self.o.mixer_we.mix_shift.eq(1)
				m.next = 'WAIT'
			with m.State('03_NOISE_VOLUME'): # 03: (v, _, _) noise vol
				m.d.sync += self.o.noise_we.vol.eq(1)
				m.next = 'WAIT'
			with m.State('04_NOISE_PERIOD'): # 04: (p, m, _) noise period/mode
				m.d.sync += self.o.noise_we.period.eq(1)
				m.d.sync += self.o.noise_we.mode.eq(1)
				m.next = 'WAIT'
			with m.State('05_SAMPLE_2'):     # 05: (a, v, _) set sample byte?
				# TODO
				m.next = 'WAIT'
			with m.State('06_SAMPLE_4'):     # 06: (a, v, w) set sample bytes?
				# TODO
				m.next = 'WAIT'
			with m.State('07_CHAN_ENABLE'):  # 07: (m, _, _) channel enable mask
				m.d.sync += self.o.sampler_i.chan_enable_we.eq(1)
				m.next = 'WAIT'
			with m.State('X0_RATE'):         # n0: (l, m, h) rate
				m.d.sync += self.o.sampler_i.chan_we.rate.eq(1)
				m.next = 'WAIT'
			with m.State('X1_RESET_PHASE'):  # n1: (_, _, _) reset phase
				# m.d.sync += self.o.sampler_i.chan_we.phase.eq(1)
				m.next = 'WAIT'
			with m.State('X2_RATE_RESET'):   # n2: (l, m, h) rate + reset phase
				# m.d.sync += self.o.sampler_i.chan_we.rate.eq(1)
				# m.d.sync += self.o.sampler_i.chan_we.phase.eq(1)
				m.next = 'WAIT'
			with m.State('X3_SAMPLE'):       # n3: (s, l, _) sample
				# m.d.sync += self.o.sampler_i.chan_we.sample.eq(1)
				m.next = 'WAIT'
			with m.State('X4_VOLUME'):       # n4: (v, _, _) volume
				# m.d.sync += self.o.sampler_i.chan_we.vol.eq(1)
				m.next = 'WAIT'

		m.d.comb += self.processing.eq(~fsm.ongoing('WAIT'))
		return m

	def dispatch(self, m):
		with m.Switch(self.i.cmd_op):
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
 			with m.Default():        m.next = 'WAIT'
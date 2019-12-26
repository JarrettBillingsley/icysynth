from nmigen import *
from nmigen.build import Platform

from constants import *
from signals import *

# --------------------------------------------------------------------------------------------------
# Wave Channel
# --------------------------------------------------------------------------------------------------

class WaveChannel(Elaboratable):
	def __init__(self, i):
		self.index = i

		# -------------------------------------
		# Inputs

		self.inputs      = WaveState()
		self.we          = WaveEnable()

		# -------------------------------------
		# Outputs

		self.sample_addr = Signal(9)
		self.sample_vol  = Signal(4)

		# -------------------------------------
		# Juicy Internals

		self.internal_state = WaveState()

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Internal State

		state = self.internal_state

		if platform:
			state.rate.reset   = CHANNEL_INIT_VALUES[self.index]['rate']
			state.length.reset = CHANNEL_INIT_VALUES[self.index]['length']
			state.start.reset  = CHANNEL_INIT_VALUES[self.index]['start']
			state.vol.reset    = CHANNEL_INIT_VALUES[self.index]['vol']

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			self.sample_addr.eq((state.phase[-9:] & state.length) + state.start),
			self.sample_vol.eq(state.vol),
		]

		# -------------------------------------
		# Sequential Logic

		with m.If(self.we.rate):
			m.d.sync += state.rate.eq(self.inputs.rate)
		with m.If(self.we.sample):
			m.d.sync += [
				state.start.eq(self.inputs.start),
				state.length.eq(self.inputs.length),
			]
		with m.If(self.we.vol):
			m.d.sync += state.vol.eq(self.inputs.vol)

		return m

	def update_phase(self, m: Module):
		s = self.internal_state
		m.d.sync += s.phase.eq((s.phase + s.rate)[:24])

	def reset_phase(self, m: Module):
		m.d.sync += self.internal_state.phase.eq(0)
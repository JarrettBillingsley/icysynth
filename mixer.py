from nmigen import *
from nmigen.build import Platform

from signals import *

# --------------------------------------------------------------------------------------------------
# Mixer
# --------------------------------------------------------------------------------------------------

class Mixer(Elaboratable):
	def __init__(self, *mix_inputs):
		self.total = sum(mix_inputs[1:], mix_inputs[0])
		self.total.name = 'total'
		self.num_bits = self.total.shape().width
		self.bits_over_8 = self.num_bits - 8
		assert self.bits_over_8 >= 0

		# -------------------------------------
		# Inputs

		self.i          = MixerState(self.bits_over_8)
		self.we         = MixerEnable()
		self.mix_inputs = mix_inputs

		# -------------------------------------
		# Outputs

		self.o = Signal(8)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		state = MixerState(self.bits_over_8)
		state.mix_shift.reset = 3

		m.d.comb += self.o.eq(self.total >> state.mix_shift)

		with m.If(self.we.mix_shift):
			m.d.sync += state.mix_shift.eq(self.i.mix_shift)

		return m
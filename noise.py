from nmigen import *
from nmigen.build import Platform

from signals import *

# --------------------------------------------------------------------------------------------------
# Noise Channel
# --------------------------------------------------------------------------------------------------

class NoiseChannel(Elaboratable):
	def __init__(self):
		# -------------------------------------
		# Inputs

		self.inputs      = NoiseState()
		self.we          = NoiseEnable()
		self.commit      = Signal()

		# TODO: BZZ mode

		# -------------------------------------
		# Outputs

		self.sound_out = Signal(8)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Internal State

		shadow  = NoiseState(name='shadow')
		state   = NoiseState(name='real')
		lfsr    = Signal(15)
		counter = Signal(16)

		lfsr.reset = 1

		if platform:
			state.period.reset = 50
			state.vol.reset    = 0xF

		# -------------------------------------
		# Combinational Logic

		m.d.comb += self.sound_out.eq(Mux(lfsr[0], Repl(state.vol, 2), 0))

		# -------------------------------------
		# Sequential Logic

		# Processing
		with m.If(counter == 0):
			m.d.sync += [
				counter.eq(state.period),
				lfsr.eq(Cat(lfsr[1:15], lfsr[0] ^ lfsr[1])),
				# TODO: BZZ mode (feedback is 0 ^ 6)
			]
		with m.Else():
			m.d.sync += counter.eq(counter - 1)

		# Writing to shadow state
		with m.If(self.we.period):
			m.d.sync += shadow.period.eq(self.inputs.period)
		with m.If(self.we.vol):
			m.d.sync += shadow.vol.eq(self.inputs.vol)

		# Committing shadow state to real state
		with m.If(self.commit):
			m.d.sync += state.eq(shadow)

		return m

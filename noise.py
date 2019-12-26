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

		self.i  = NoiseState()
		self.we = NoiseEnable()

		# -------------------------------------
		# Outputs

		self.o = Signal(8)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Internal State

		state   = NoiseState()
		lfsr    = Signal(15)
		counter = Signal(16) # TODO: does this counter really need to be 16b?

		lfsr.reset = 1

		if platform:
			state.period.reset = 50
			state.vol.reset    = 0xF

		# -------------------------------------
		# Combinational Logic

		m.d.comb += self.o.eq(Mux(lfsr[0], Repl(state.vol, 2), 0))

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

		# Writing to state
		with m.If(self.we.period):
			m.d.sync += state.period.eq(self.i.period)
		with m.If(self.we.vol):
			m.d.sync += state.vol.eq(self.i.vol)

		return m

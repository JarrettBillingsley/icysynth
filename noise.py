from amaranth import *
from amaranth.build import Platform

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
		counter = Signal(16)

		lfsr.reset = 1

		if TESTING:
			state.period.reset = 1
			state.vol.reset    = 0xF

		# -------------------------------------
		# Combinational Logic

		m.d.comb += self.o.eq(Mux(lfsr[0], Repl(state.vol, 2), 0))

		# -------------------------------------
		# Sequential Logic

		# Processing
		with m.If(counter == 0):
			m.d.sync += [
				counter.eq(state.period << 8),
				lfsr.eq(Mux(
					state.mode,
					Cat(lfsr[1:15], lfsr[0] ^ lfsr[6]),
					Cat(lfsr[1:15], lfsr[0] ^ lfsr[1]))),
			]
		with m.Else():
			m.d.sync += counter.eq(counter - 1)

		# Writing to state
		with m.If(self.we.period):
			m.d.sync += state.period.eq(self.i.period)
		with m.If(self.we.mode):
			m.d.sync += state.mode.eq(self.i.mode)
		with m.If(self.we.vol):
			m.d.sync += state.vol.eq(self.i.vol)

		return m

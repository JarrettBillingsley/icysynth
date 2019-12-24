from nmigen import *
from nmigen.build import Platform

# --------------------------------------------------------------------------------------------------
# PWM
# --------------------------------------------------------------------------------------------------

class PWM(Elaboratable):
	def __init__(self):
		self.i = Signal(8)
		self.o = Signal()

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		counter = Signal(8)

		m.d.comb += self.o.eq(counter < self.i)
		m.d.sync += counter.eq(counter + 1)

		return m
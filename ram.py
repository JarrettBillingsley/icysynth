from amaranth import *
from amaranth.build import Platform

from constants import *

# --------------------------------------------------------------------------------------------------
# Sample RAM
# --------------------------------------------------------------------------------------------------

class SampleRam(Elaboratable):
	def __init__(self):
		# -------------------------------------
		# Inputs

		self.waddr = Signal(SAMPLE_ADDR_BITS)
		self.wdata = Signal(2 * SAMPLE_BITS)
		self.we    = Signal(1)

		self.raddr = Signal(SAMPLE_ADDR_BITS)

		# -------------------------------------
		# Outputs

		self.rdata_0 = Signal(SAMPLE_BITS)
		self.rdata_1 = Signal(SAMPLE_BITS)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		mem = Memory(
			width = 2 * SAMPLE_BITS,
			depth = (1 << SAMPLE_ADDR_BITS),
			init = DUMMY_RAM,
			name = 'sample_ram'
		)
		m.submodules.rdport = rdport = mem.read_port()
		m.submodules.wrport = wrport = mem.write_port()

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			wrport.addr.eq(self.waddr),
			wrport.data.eq(self.wdata),
			wrport.en.  eq(self.we),

			rdport.addr.eq(self.raddr),
			self.rdata_0.eq(rdport.data[-4:]),
			self.rdata_1.eq(rdport.data[:4]),
		]

		return m

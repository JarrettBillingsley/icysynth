from amaranth import *
from amaranth.build import Platform

# --------------------------------------------------------------------------------------------------
# Volume Table ROM
# --------------------------------------------------------------------------------------------------

# exact same volume table generator code as the original
def make_voltab():
	maxvol = [
		0x00, 0x11, 0x22, 0x33,
		0x44, 0x55, 0x66, 0x77,
		0x88, 0x99, 0xAA, 0xBB,
		0xCC, 0xDD, 0xEE, 0xFF]

	def lerp(samp, max):
		return int(samp / 0xF * max)
	i = 0
	ret = [0] * 256

	for vol in range(0, 16):
		for samp in range(0, 16):
			ret[i] = lerp(samp, maxvol[vol])
			i += 1

	return ret

class VolumeRom(Elaboratable):
	def __init__(self):
		# -------------------------------------
		# Inputs

		self.addr = Signal(8)

		# -------------------------------------
		# Outputs

		self.rdat = Signal(8)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		mem = Memory(width = 8, depth = 256, init = make_voltab(), name = 'volume_rom')
		m.submodules.rdport = rdport = mem.read_port()

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			rdport.addr.eq(self.addr),
			self.rdat.  eq(rdport.data),
		]

		return m
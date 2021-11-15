from nmigen import *
from nmigen.build import Platform

from rom import *
from signals import *

# --------------------------------------------------------------------------------------------------
# Sampler
# --------------------------------------------------------------------------------------------------

class PhaseAdder(Elaboratable):
	def __init__(self):
		self.A = Signal(PHASE_BITS)
		self.B = Signal(PHASE_BITS)
		self.Y = Signal(PHASE_BITS)

	def elaborate(self, platform):
		m = Module()

		m.d.comb += self.Y.eq((self.A + self.B)[:PHASE_BITS])

		return m

class PhaseRam(Elaboratable):
	def __init__(self):
		# -------------------------------------
		# Inputs

		self.addr  = Signal(range(NUM_CHANNELS))
		self.wdata = Signal(PHASE_BITS)
		self.we    = Signal(1)

		# -------------------------------------
		# Outputs

		self.rdata = Signal(PHASE_BITS)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		mem_lo = Memory(
			width = 16,
			depth = NUM_CHANNELS,
			name = 'phase_ram_lo'
		)
		m.submodules.rdport_lo = rdport_lo = mem_lo.read_port()
		m.submodules.wrport_lo = wrport_lo = mem_lo.write_port()

		mem_hi = Memory(
			width = 8,
			depth = NUM_CHANNELS,
			name = 'phase_ram_hi',
			# override the BRAM efficiency calculations and force this into a BRAM
			attrs = {"ram_block": True}
		)
		m.submodules.rdport_hi = rdport_hi = mem_hi.read_port()
		m.submodules.wrport_hi = wrport_hi = mem_hi.write_port()

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			wrport_lo.addr.eq(self.addr),
			wrport_hi.addr.eq(self.addr),
			wrport_lo.data.eq(self.wdata[:16]),
			wrport_hi.data.eq(self.wdata[-8:]),
			wrport_lo.en.  eq(self.we),
			wrport_hi.en.  eq(self.we),

			rdport_lo.addr.eq(self.addr),
			rdport_hi.addr.eq(self.addr),
			self.rdata.eq(Cat(rdport_lo.data, rdport_hi.data)),
		]

		return m

class RateRam(Elaboratable):
	def __init__(self):
		# -------------------------------------
		# Inputs

		self.addr  = Signal(range(NUM_CHANNELS))
		self.wdata = Signal(PHASE_BITS)
		self.we    = Signal(1)

		# -------------------------------------
		# Outputs

		self.rdata = Signal(PHASE_BITS)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		init = None

		if TESTING:
			init = [CHANNEL_INIT_VALUES[i]['rate'] for i in range(NUM_CHANNELS)]

		mem = Memory(
			width = PHASE_BITS,
			depth = NUM_CHANNELS,
			name = 'rate_ram',
			init = init
		)
		m.submodules.rdport = rdport = mem.read_port()
		m.submodules.wrport = wrport = mem.write_port()

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			wrport.addr.eq(self.addr),
			wrport.data.eq(self.wdata),
			wrport.en.  eq(self.we),

			rdport.addr.eq(self.addr),
			self.rdata.eq(rdport.data),
		]

		return m

class Sampler(Elaboratable):
	def __init__(self, num_channels: int, sample_cycs: int):
		assert sample_cycs >= (2 * num_channels) + 2, "sample period too short!"

		self.num_channels = num_channels
		self.sample_cycs  = sample_cycs
		self.acc_range    = 0xFF * num_channels

		# -------------------------------------
		# Inputs

		self.i = SamplerInput(num_channels)

		# -------------------------------------
		# Outputs

		self.o        = Signal(range(self.acc_range))
		self.ram_addr = Signal(SAMPLE_ADDR_BITS)
		self.busy     = Signal()

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		m.submodules.volume_rom  = volume_rom  = VolumeRom()
		m.submodules.phase_adder = phase_adder = PhaseAdder()
		m.submodules.phase_ram   = phase_ram   = PhaseRam()
		m.submodules.rate_ram    = rate_ram    = RateRam()

		# -------------------------------------
		# Internal state

		channels      = Array([WaveState(name = f'ch_{i}') for i in range(self.num_channels)])
		acc           = Signal(range(self.acc_range))
		cycle_counter = Signal(range(self.sample_cycs))
		chan_enable   = Signal(self.num_channels)
		phase_reset   = Signal(self.num_channels)

		if TESTING:
			chan_enable.reset = ~0

			for i, ch in enumerate(channels):
				ch.length.reset = CHANNEL_INIT_VALUES[i]['length']
				ch.start.reset  = CHANNEL_INIT_VALUES[i]['start']
				ch.vol.reset    = CHANNEL_INIT_VALUES[i]['vol']

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			rate_ram.wdata.eq(self.i.chan_i.rate),

			phase_adder.A.eq(phase_ram.rdata),
			phase_adder.B.eq(rate_ram.rdata),
			phase_ram.wdata.eq(phase_adder.Y),
		]

		# -------------------------------------
		# Sequential Logic

		m.d.sync += rate_ram.we.eq(0)
		m.d.sync += phase_ram.we.eq(0)

		# Sampler state
		with m.If(self.i.chan_enable_we):
			m.d.sync += chan_enable.eq(self.i.chan_enable)

		# Channel state
		# for i, ch in enumerate(channels):
			# with m.If(self.i.chan_select == i):
		with m.If(self.i.chan_we.rate):
			# m.d.sync += channels[self.i.chan_select].rate.eq(self.i.chan_i.rate)
			m.d.comb += rate_ram.addr.eq(self.i.chan_select)
			m.d.sync += rate_ram.we.eq(1)
		with m.If(self.i.chan_we.phase):
			m.d.sync += phase_reset.eq(phase_reset | (1 << self.i.chan_select))
		with m.If(self.i.chan_we.sample):
			m.d.sync += channels[self.i.chan_select].start.eq(self.i.chan_i.start)
			m.d.sync += channels[self.i.chan_select].length.eq(self.i.chan_i.length),
		with m.If(self.i.chan_we.vol):
			m.d.sync += channels[self.i.chan_select].vol.eq(self.i.chan_i.vol)

		# Sequencing
		m.d.sync += cycle_counter.eq(cycle_counter + 1)

		with m.FSM(name='mix_fsm') as fsm:
			for i, ch in enumerate(channels):
				with m.State(f'UPDATE{i}'):
					with m.If(phase_reset[i]):
						m.d.comb += phase_ram.wdata.eq(0)

					m.d.comb += phase_ram.addr.eq(i)
					m.d.comb += rate_ram.addr.eq(i)
					m.d.sync += phase_ram.we.eq(1)
					m.next = f'SAMP_FETCH{i}'

				with m.State(f'SAMP_FETCH{i}'):
					m.d.comb += phase_ram.addr.eq(i)

					offs = phase_ram.rdata[-SAMPLE_ADDR_BITS:] & ch.length
					m.d.comb += self.ram_addr.eq(offs + ch.start)
					m.next = f'VOL_FETCH{i}'

				with m.State(f'VOL_FETCH{i}'):
					m.d.comb += phase_ram.addr.eq(i)

					which = phase_ram.rdata[-SAMPLE_ADDR_BITS - 1]
					samp = Mux(which, self.i.ram_data_1, self.i.ram_data_0)
					m.d.comb += volume_rom.addr.eq(Cat(samp, ch.vol))
					m.next = f'ACCUM{i}'

				with m.State(f'ACCUM{i}'):
					with m.If(chan_enable[i]):
						m.d.sync += acc.eq(acc + volume_rom.rdat)

					m.next = 'OUTPUT' if i == self.num_channels - 1 else f'UPDATE{i+1}'

			with m.State('OUTPUT'):
				m.d.sync += self.o.eq(acc)
				m.d.sync += acc.eq(0)
				m.d.sync += phase_reset.eq(0)
				m.next = 'WAIT'

			with m.State('WAIT'):
				with m.If(cycle_counter == self.sample_cycs - 1):
					m.d.sync += cycle_counter.eq(0)
					m.next = 'UPDATE0'

		m.d.comb += self.busy.eq(~fsm.ongoing('WAIT'))
		return m
from nmigen import *
from nmigen.build import Platform

from rom import *
from signals import *

# --------------------------------------------------------------------------------------------------
# Sampler
# --------------------------------------------------------------------------------------------------

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

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		m.submodules.volume_rom = volume_rom = VolumeRom()

		# -------------------------------------
		# Internal state

		channels      = Array([WaveState(name = f'ch_{i}') for i in range(self.num_channels)])
		acc           = Signal(range(self.acc_range))
		cycle_counter = Signal(range(self.sample_cycs))
		chan_enable   = Signal(self.num_channels)
		phase_reset   = Signal(self.num_channels)

		if platform:
			chan_enable.reset = ~0

			for i, ch in enumerate(channels):
				ch.rate.reset   = CHANNEL_INIT_VALUES[i]['rate']
				ch.length.reset = CHANNEL_INIT_VALUES[i]['length']
				ch.start.reset  = CHANNEL_INIT_VALUES[i]['start']
				ch.vol.reset    = CHANNEL_INIT_VALUES[i]['vol']

		# -------------------------------------
		# Sequential Logic

		# Sampler state
		with m.If(self.i.chan_enable_we):
			m.d.sync += chan_enable.eq(self.i.chan_enable)

		# Channel state
		for i, ch in enumerate(channels):
			with m.If(self.i.chan_select == i):
				with m.If(self.i.chan_we.rate):
					m.d.sync += ch.rate.eq(self.i.chan_i.rate)
				with m.If(self.i.chan_we.phase):
					m.d.sync += phase_reset.eq(phase_reset | 1 << i)
				with m.If(self.i.chan_we.sample):
					m.d.sync += ch.start.eq(self.i.chan_i.start)
					m.d.sync += ch.length.eq(self.i.chan_i.length),
				with m.If(self.i.chan_we.vol):
					m.d.sync += ch.vol.eq(self.i.chan_i.vol)

		# Sequencing
		m.d.sync += cycle_counter.eq(cycle_counter + 1)

		with m.FSM(name='mix_fsm') as fsm:
			with m.State('OUTPUT'):
				m.d.sync += self.o.eq(acc)
				m.d.sync += acc.eq(0)
				m.d.sync += phase_reset.eq(0)
				m.next = 'UPDATE0'

			for i, ch in enumerate(channels):
				with m.State(f'UPDATE{i}'):
					with m.If(chan_enable[i]):
						with m.If(phase_reset[i]):
							m.d.sync += ch.phase.eq(0)
						with m.Else():
							m.d.sync += ch.phase.eq((ch.phase + ch.rate)[:PHASE_BITS])

					m.next = f'SAMP_FETCH{i}'

				with m.State(f'SAMP_FETCH{i}'):
					offs = ch.phase[-SAMPLE_ADDR_BITS:] & ch.length
					m.d.comb += self.ram_addr.eq(offs + ch.start)
					m.next = f'VOL_FETCH{i}'

				with m.State(f'VOL_FETCH{i}'):
					m.d.comb += volume_rom.addr.eq(Cat(self.i.ram_data, ch.vol))
					m.next = f'ACCUM{i}'

				with m.State(f'ACCUM{i}'):
					with m.If(chan_enable[i]):
						m.d.sync += acc.eq(acc + volume_rom.rdat)

					m.next = 'WAIT' if i == self.num_channels - 1 else f'UPDATE{i+1}'

			with m.State('WAIT'):
				with m.If(cycle_counter == self.sample_cycs - 1):
					m.d.sync += cycle_counter.eq(0)
					m.next = 'OUTPUT'

		return m
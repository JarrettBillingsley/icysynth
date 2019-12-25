from nmigen import *
from nmigen.build import Platform

from wave import *
from noise import *
from rom import *
from signals import *

# --------------------------------------------------------------------------------------------------
# Mixer
# --------------------------------------------------------------------------------------------------

class Mixer(Elaboratable):
	def __init__(self, num_channels: int, sample_cycs: int):
		assert sample_cycs >= num_channels + 2, "sample period too short!"

		self.num_channels = num_channels
		self.acc_range = 0xFF * (num_channels + 1)
		self.sample_cycs = sample_cycs

		# -------------------------------------
		# Inputs

		self.i = MixerInput(num_channels)
		self.sample_ram_data = Signal(4)

		# -------------------------------------
		# Outputs

		self.o = Signal(range(self.acc_range))
		self.sample_ram_addr  = Signal(9)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		volume_rom = VolumeRom()
		channels   = Array([WaveChannel(i) for i in range(self.num_channels)])
		noise      = NoiseChannel()

		m.submodules.volume_rom = volume_rom

		for (i, c) in enumerate(channels):
			m.submodules[f'ch_{i}'] = c

		m.submodules.noise = noise

		# -------------------------------------
		# Internal state

		state  = MixerState(self.num_channels)
		state.mix_shift.reset = 3

		acc           = Signal(range(self.acc_range))
		cycle_counter = Signal(range(self.sample_cycs))
		phase_reset   = Signal(self.num_channels)

		if platform:
			state.chan_enable.reset = ~0

		# -------------------------------------
		# Combinational Logic

		for i in range(self.num_channels):
			m.d.comb += channels[i].inputs.eq(self.i.chan_inputs)

			with m.If(self.i.chan_select == i):
				m.d.comb += channels[i].we.eq(self.i.chan_we)

		m.d.comb += [
			noise.inputs.eq(self.i.noise_inputs),
			noise.we.eq(self.i.noise_we),
		]

		mixed_waves = Signal(range(self.acc_range))

		m.d.comb += self.o.eq((mixed_waves + noise.sound_out) >> state.mix_shift)

		# -------------------------------------
		# Sequential Logic

		m.d.sync += cycle_counter.eq(cycle_counter + 1)

		with m.If(self.i.chan_we.phase):
			m.d.sync += phase_reset.eq(phase_reset | i << self.i.chan_select)

		with m.If(self.i.we.chan_enable):
			m.d.sync += state.chan_enable.eq(self.i.inputs.chan_enable)
		with m.If(self.i.we.mix_shift):
			m.d.sync += state.mix_shift.eq(self.i.inputs.mix_shift)

		with m.FSM(name='mix_fsm') as fsm:
			with m.State('OUTPUT'):
				# ASSUME: cycle_counter == 0
				m.d.sync += [
					mixed_waves.eq(acc),
					acc.eq(0),
					phase_reset.eq(0),
				]

				m.next = 'UPDATE0'

			for i in range(self.num_channels):
				with m.State(f'UPDATE{i}'):
					with m.If(state.chan_enable[i]):
						with m.If(phase_reset[i]):
							channels[i].reset_phase(m)
						with m.Else():
							channels[i].update_phase(m)
					m.next = f'ACCUM{i}'

			for i in range(self.num_channels):
				# ASSUME: cycle_counter == 1 .. num_channels
				with m.State(f'ACCUM{i}'):
					with m.If(state.chan_enable[i]):
						m.d.comb += [
							self.sample_ram_addr.eq(channels[i].sample_addr),
							volume_rom.addr.eq(Cat(self.sample_ram_data, channels[i].sample_vol)),
						]

						m.d.sync += [
							acc.eq(acc + volume_rom.rdat)
						]

					if i == self.num_channels - 1:
						m.next = 'WAIT'
					else:
						m.next = f'UPDATE{i+1}'

			with m.State('WAIT'):
				# ASSUME: cycle_counter == num_channels + 1 .. sample_cycs - 1

				with m.If(cycle_counter == self.sample_cycs - 1):
					m.d.sync += cycle_counter.eq(0)
					m.next = 'OUTPUT'

		return m
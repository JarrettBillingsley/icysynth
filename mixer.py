from nmigen import *
from nmigen.build import Platform

from wave import *
from noise import *
from ram import *
from rom import *

# --------------------------------------------------------------------------------------------------
# Mixer
# --------------------------------------------------------------------------------------------------

class MixerState(Record):
	def __init__(self, num_channels, name=None):
		super().__init__([
			('chan_enable',  num_channels),
			('mix_shift',    2),
		], name=name)

class MixerEnable(Record):
	def __init__(self):
		super().__init__([
			('chan_enable', 1),
			('mix_shift',   1),
		])

class Mixer(Elaboratable):
	def __init__(self, num_channels: int, sample_cycs: int):
		assert sample_cycs >= num_channels + 2, "sample period too short!"

		self.num_channels = num_channels
		self.acc_range = 0xFF * num_channels
		self.sample_cycs = sample_cycs

		# -------------------------------------
		# Inputs

		self.inputs       = MixerState(num_channels)
		self.we           = MixerEnable()
		self.commit       = Signal()

		self.chan_select  = Signal(range(num_channels))
		self.chan_inputs  = WaveState()
		self.chan_we      = WaveEnable()

		self.noise_inputs = NoiseState()
		self.noise_we     = NoiseEnable()

		# -------------------------------------
		# Outputs

		self.mixer_out  = Signal(range(self.acc_range))

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		sample_ram = SampleRam()
		volume_rom = VolumeRom()
		channels   = Array([WaveChannel(i) for i in range(self.num_channels)])
		noise      = NoiseChannel()

		m.submodules.sample_ram = sample_ram
		m.submodules.volume_rom = volume_rom

		for (i, c) in enumerate(channels):
			m.submodules[f'ch_{i}'] = c

		m.submodules.noise = noise

		# -------------------------------------
		# Internal state

		shadow = MixerState(self.num_channels, name='shadow')
		state  = MixerState(self.num_channels, name='real')
		shadow.mix_shift.reset = 3
		state.mix_shift.reset = 3

		acc           = Signal(range(self.acc_range))
		cycle_counter = Signal(range(self.sample_cycs))

		if platform:
			state.chan_enable.reset = 0xFF

		# -------------------------------------
		# Combinational Logic

		for i in range(self.num_channels):
			m.d.comb += [
				channels[i].commit.eq(self.commit),
				channels[i].inputs.eq(self.chan_inputs),
			]

			with m.If(self.chan_select == i):
				m.d.comb += channels[i].we.eq(self.chan_we)

		m.d.comb += [
			noise.inputs.eq(self.noise_inputs),
			noise.we.eq(self.noise_we),
			noise.commit.eq(self.commit),
		]

		sample_out = Signal(range(self.acc_range))

		m.d.comb += self.mixer_out.eq((sample_out + noise.sound_out) >> state.mix_shift)

		# -------------------------------------
		# Sequential Logic

		m.d.sync += cycle_counter.eq(cycle_counter + 1)

		with m.If(self.we.chan_enable):
			m.d.sync += shadow.chan_enable.eq(self.inputs.chan_enable)
		with m.If(self.we.mix_shift):
			m.d.sync += shadow.mix_shift.eq(self.inputs.mix_shift)

		# TODO: race condition between commit and update/accum.
		# presumably it should only commit during wait state,
		# but don't wanna lose commits that come in during not-wait states.
		# or would this be handled at a higher interface layer?
		# and this just outputs a signal saying if commits are OK?
		with m.If(self.commit):
			m.d.sync += state.eq(shadow)

		with m.FSM(name='mix_fsm') as fsm:
			with m.State('UPDATE'):
				# ASSUME: cycle_counter == 0
				for i in range(self.num_channels):
					m.d.comb += channels[i].enabled.eq(state.chan_enable[i])

				m.d.sync += [
					sample_out.eq(acc),
					acc.eq(0),
				]

				m.next = 'ACCUM0'

			for i in range(self.num_channels):
				# ASSUME: cycle_counter == 1 .. num_channels
				with m.State(f'ACCUM{i}'):
					with m.If(state.chan_enable[i]):
						m.d.comb += [
							sample_ram.addr.eq(channels[i].sample_addr),
							volume_rom.addr.eq(Cat(sample_ram.rdat, channels[i].sample_vol)),
						]

						m.d.sync += [
							acc.eq(acc + volume_rom.rdat)
						]

					if i == self.num_channels - 1:
						m.next = 'WAIT'
					else:
						m.next = f'ACCUM{i+1}'

			with m.State('WAIT'):
				# ASSUME: cycle_counter == num_channels + 1 .. sample_cycs - 1

				with m.If(cycle_counter == self.sample_cycs - 1):
					m.d.sync += cycle_counter.eq(0)
					m.next = 'UPDATE'

		return m
from enum import Enum, unique, auto
from argparse import ArgumentParser

from nmigen import *
from nmigen.build import Platform, Resource, Subsignal, Pins
from nmigen.back import verilog
from nmigen.back.pysim import *
from nmigen.hdl.rec import *

# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------

CLK_RATE      = 12000000
KHZ           = 1000
MHZ           = 1000 * KHZ
SAMPLE_RATE   = 46875
SAMPLE_CYCS   = CLK_RATE // SAMPLE_RATE
SAMPLE_PERIOD = 1 / SAMPLE_CYCS
CLK_PERIOD    = 1 / CLK_RATE
NUM_CHANNELS  = 8

# --------------------------------------------------------------------------------------------------
# Sample RAM
# --------------------------------------------------------------------------------------------------

DUMMY_RAM = [
	# sine
	0x8, 0x8, 0x9, 0xA, 0xB, 0xB, 0xC, 0xD, 0xD, 0xE, 0xE, 0xF, 0xF, 0xF, 0xF, 0xF,
	0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xE, 0xE, 0xD, 0xD, 0xC, 0xB, 0xB, 0xA, 0x9, 0x8,
	0x8, 0x7, 0x6, 0x5, 0x4, 0x4, 0x3, 0x2, 0x2, 0x1, 0x1, 0x1, 0x0, 0x0, 0x0, 0x0,
	0x0, 0x0, 0x0, 0x0, 0x0, 0x1, 0x1, 0x1, 0x2, 0x2, 0x3, 0x4, 0x4, 0x5, 0x6, 0x7,

	# saw
	0x0, 0x0, 0x0, 0x0, 0x1, 0x1, 0x1, 0x1, 0x2, 0x2, 0x2, 0x2, 0x3, 0x3, 0x3, 0x3,
	0x4, 0x4, 0x4, 0x4, 0x5, 0x5, 0x5, 0x5, 0x6, 0x6, 0x6, 0x6, 0x7, 0x7, 0x7, 0x7,
	0x8, 0x8, 0x8, 0x8, 0x9, 0x9, 0x9, 0x9, 0xA, 0xA, 0xA, 0xA, 0xB, 0xB, 0xB, 0xB,
	0xC, 0xC, 0xC, 0xC, 0xD, 0xD, 0xD, 0xD, 0xE, 0xE, 0xE, 0xE, 0xF, 0xF, 0xF, 0xF,

	# tri
	0x0, 0x0, 0x1, 0x1, 0x2, 0x2, 0x3, 0x3, 0x4, 0x4, 0x5, 0x5, 0x6, 0x6, 0x7, 0x7,
	0x8, 0x8, 0x9, 0x9, 0xA, 0xA, 0xB, 0xB, 0xC, 0xC, 0xD, 0xD, 0xE, 0xE, 0xF, 0xF,
	0xF, 0xF, 0xE, 0xE, 0xD, 0xD, 0xC, 0xC, 0xB, 0xB, 0xA, 0xA, 0x9, 0x9, 0x8, 0x8,
	0x7, 0x7, 0x6, 0x6, 0x5, 0x5, 0x4, 0x4, 0x3, 0x3, 0x2, 0x2, 0x1, 0x1, 0x0, 0x0,

	# square
	0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
	0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
	0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF,
	0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF,
] + [0] * 256

class SampleRam(Elaboratable):
	def __init__(self):
		# -------------------------------------
		# Inputs

		self.addr = Signal(9)
		self.wdat = Signal(4)
		self.we   = Signal(1)

		# -------------------------------------
		# Outputs

		self.rdat = Signal(4)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		mem = Memory(width = 4, depth = 512, init = DUMMY_RAM)
		m.submodules.rdport = rdport = mem.read_port()
		m.submodules.wrport = wrport = mem.write_port()

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			wrport.addr.eq(self.addr),
			wrport.data.eq(self.wdat),
			wrport.en.  eq(self.we),

			rdport.addr.eq(self.addr),
			self.rdat.  eq(rdport.data),
		]

		return m

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

		mem = Memory(width = 8, depth = 256, init = make_voltab())
		m.submodules.rdport = rdport = mem.read_port()

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			rdport.addr.eq(self.addr),
			self.rdat.  eq(rdport.data),
		]

		return m

# --------------------------------------------------------------------------------------------------
# Wave Channel
# --------------------------------------------------------------------------------------------------

class WaveState(Record):
	def __init__(self, name=None):
		super().__init__([
			('phase',  24),
			('rate',   24),
			('start',  9),
			('length', 9),
			('vol',    4),
		], name=name)

class WaveEnable(Record):
	def __init__(self):
		super().__init__([
			('phase',  1),
			('rate',   1),
			('sample', 1),
			('vol',    1),
		])

class WaveChannel(Elaboratable):
	def __init__(self, i):
		self.index = i

		# -------------------------------------
		# Inputs

		self.inputs      = WaveState()
		self.we          = WaveEnable()
		self.commit      = Signal()
		self.enabled     = Signal()

		# -------------------------------------
		# Outputs

		self.sample_addr = Signal(9)
		self.sample_vol  = Signal(4)

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Internal State

		phase_dirty = Signal(1)
		shadow      = WaveState(name='shadow')
		state       = WaveState(name='real')

		if platform:
			state.rate.reset   = CHANNEL_INIT_VALUES[self.index]['rate']
			state.length.reset = CHANNEL_INIT_VALUES[self.index]['length']
			state.start.reset  = CHANNEL_INIT_VALUES[self.index]['start']
			state.vol.reset    = CHANNEL_INIT_VALUES[self.index]['vol']

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			self.sample_addr.eq((state.phase[-9:] & state.length) + state.start),
			self.sample_vol.eq(state.vol),
		]

		# -------------------------------------
		# Sequential Logic

		# Processing
		with m.If(self.enabled):
			m.d.sync += state.phase.eq((state.phase + state.rate)[0:24])

		# Writing to shadow state
		with m.If(self.we.phase):
			m.d.sync += [
				shadow.phase.eq(self.inputs.phase),
				phase_dirty.eq(1),
			]
		with m.If(self.we.rate):
			m.d.sync += shadow.rate.eq(self.inputs.rate)
		with m.If(self.we.sample):
			m.d.sync += [
				shadow.start.eq(self.inputs.start),
				shadow.length.eq(self.inputs.length),
			]
		with m.If(self.we.vol):
			m.d.sync += shadow.vol.eq(self.inputs.vol)

		# Committing shadow state to real state
		with m.If(self.commit):
			m.d.sync += [
				state.rate.  eq(shadow.rate  ),
				state.start. eq(shadow.start ),
				state.length.eq(shadow.length),
				state.vol.   eq(shadow.vol   ),
			]

			with m.If(phase_dirty):
				m.d.sync += [
					state.phase.eq(shadow.phase),
					phase_dirty.eq(0),
				]

		return m

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

		self.inputs      = MixerState(num_channels)
		self.we          = MixerEnable()
		self.commit      = Signal()

		self.chan_select = Signal(range(num_channels))
		self.chan_inputs = WaveState()
		self.chan_we     = WaveEnable()

		# -------------------------------------
		# Outputs

		self.sample_out  = Signal(range(self.acc_range))

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Submodules

		sample_ram = SampleRam()
		channels   = Array([WaveChannel(i) for i in range(self.num_channels)])

		volume_rom = VolumeRom()
		cycle_counter = Signal(range(self.sample_cycs))

		m.submodules.sample_ram = sample_ram
		m.submodules.volume_rom = volume_rom

		for (i, c) in enumerate(channels):
			m.submodules[f'ch_{i}'] = c

		# -------------------------------------
		# Internal state

		shadow = MixerState(self.num_channels, name='shadow')
		state  = MixerState(self.num_channels, name='real')


		acc    = Signal(range(self.acc_range))
		shadow.mix_shift.reset = 3
		state.mix_shift.reset = 3

		# -------------------------------------
		# Combinational Logic

		for i in range(self.num_channels):
			m.d.comb += [
				channels[i].commit.eq(self.commit),
				channels[i].inputs.eq(self.chan_inputs),
			]

			with m.If(self.chan_select == i):
				m.d.comb += channels[i].we.eq(self.chan_we)


		if platform:
			state.chan_enable.reset = 0xFF

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
					self.sample_out.eq(acc >> state.mix_shift),
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

# --------------------------------------------------------------------------------------------------
# Testing
# --------------------------------------------------------------------------------------------------

def toggle_enable(*sig):
	for s in sig:
		yield s.eq(1)
	yield

	for s in sig:
		yield s.eq(0)

CHANNEL_INIT_VALUES = [
	{ 'rate': 0x008000, 'length': 0x3F, 'start': 0x00, 'vol': 0x0F }, # 0
	{ 'rate': 0x00C000, 'length': 0x3F, 'start': 0x00, 'vol': 0x0F }, # 1
	{ 'rate': 0x012000, 'length': 0x3F, 'start': 0x00, 'vol': 0x0F }, # 2
	{ 'rate': 0x024000, 'length': 0x3F, 'start': 0x00, 'vol': 0x0F }, # 3
	{ 'rate': 0x004000, 'length': 0x3F, 'start': 0x40, 'vol': 0x0F }, # 4
	{ 'rate': 0x006000, 'length': 0x3F, 'start': 0x40, 'vol': 0x0F }, # 5
	{ 'rate': 0x009000, 'length': 0x3F, 'start': 0x40, 'vol': 0x0F }, # 6
	{ 'rate': 0x012000, 'length': 0x3F, 'start': 0x40, 'vol': 0x0F }, # 7
]

def setup_channel(mix, i, values):
	yield mix.chan_select.eq(i)
	yield mix.chan_inputs.rate.eq(values['rate'])
	yield mix.chan_inputs.length.eq(values['length'])
	yield mix.chan_inputs.start.eq(values['start'])
	yield mix.chan_inputs.vol.eq(values['vol'])
	yield from toggle_enable(mix.chan_we.rate, mix.chan_we.sample, mix.chan_we.vol)

def test_proc(mix):
	# setup channels
	for i in range(NUM_CHANNELS):
		yield from setup_channel(mix, i, CHANNEL_INIT_VALUES[i])

	# setup mixer state
	yield mix.inputs.chan_enable.eq(0xFF)
	yield from toggle_enable(mix.we.chan_enable)
	yield from toggle_enable(mix.commit)

SIM_CLOCKS = 3000

def simulate(dut):
	sim = Simulator(dut)
	sim.add_clock(CLK_PERIOD)

	def fuckyou():
		yield from test_proc(dut.submodules.mixer)
	sim.add_sync_process(fuckyou)

	# BUG: nmigen currently ignores the 'traces' param on this function,
	# so the resulting gtkw isn't very useful.
	with sim.write_vcd("out.vcd"):
		sim.run_until(CLK_PERIOD * SIM_CLOCKS, run_passive = True)

# --------------------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------------------

def parse_args():
	parser = ArgumentParser()
	p_action = parser.add_subparsers(dest="action")
	p_action.add_parser("simulate")
	p_action.add_parser("generate")
	p_action.add_parser("program")

	return parser.parse_args()

if __name__ == "__main__":
	dut = Module()
	dut.submodules.mixer = Mixer(NUM_CHANNELS, SAMPLE_CYCS)
	dut.submodules.pwm = PWM()

	dut.d.comb += dut.submodules.pwm.i.eq(dut.submodules.mixer.sample_out[:8])

	args = parse_args()

	if args.action == "simulate":
		simulate(dut)
	elif args.action == "generate":
		v = verilog.convert(dut, name = "top")

		with open('icysynth.v', 'w') as f:
			print(v, file=f)
	elif args.action == "program":
		from nmigen_boards.icestick import *

		platform = ICEStickPlatform()

		platform.add_resources([
			Resource("sound_out", 0,
				Subsignal("pin", Pins('3', conn=('j', 1), dir='o')),
			)
		])

		dut.d.comb += platform.request('sound_out').pin.eq(dut.submodules.pwm.o)

		platform.build(dut, do_program=True)
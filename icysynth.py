from argparse import ArgumentParser

from amaranth import *
from amaranth.build import Platform, Resource, Subsignal, Pins
from amaranth.back import verilog
from amaranth.sim import *
from amaranth.hdl.rec import *

from cmd import *
from constants import *
from mixer import *
from noise import *
from pll import *
from pwm import *
from ram import *
from sampler import *
from serial_cmd import *
from sim import *
from term import connect_over_serial
from uart import *

# IDEAS:
# - stereo (maybe simple like genesis/GB)
# - echo (using a RAM?)

# --------------------------------------------------------------------------------------------------
# The synth as a single module
# --------------------------------------------------------------------------------------------------

class IcySynth(Elaboratable):
	def __init__(self, num_channels: int, sample_cycs: int, baudrate: int):
		self.num_channels = num_channels
		self.baudrate = baudrate

		self.sample_ram = SampleRam()
		self.sampler    = Sampler(num_channels, sample_cycs)
		self.noise      = NoiseChannel()
		self.mixer      = Mixer(self.sampler.o, self.noise.o)
		self.pwm        = PWM()
		self.o          = Signal()
		pass

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		uart_freq = BAUDRATE * 2

		if platform:
			pll = PLL(platform.default_clk_frequency / 1_000_000, CLK_RATE / 1_000_000)
			# overrides the default 'sync' domain
			m.domains += pll.domain
			m.submodules.pll = pll
			m.d.comb += pll.clk_pin.eq(platform.request(platform.default_clk, dir='-'))

			uart_freq = int(pll.best_fout * 1_000_000)

		self.uart = UartCmd(self.baudrate, uart_freq)
		self.cmd = Cmd(self.num_channels, self.mixer.bits_over_8)

		m.submodules.cmd        = self.cmd
		m.submodules.uart       = self.uart
		m.submodules.sample_ram = self.sample_ram
		m.submodules.sampler    = self.sampler
		m.submodules.noise      = self.noise
		m.submodules.mixer      = self.mixer
		m.submodules.pwm        = self.pwm

		m.d.comb += [
			# UART <-> CMD
			self.cmd.i.eq(self.uart.o),
			self.uart.processing.eq(self.cmd.processing),

			# CMD -> Sampler
			self.sampler.i.eq(self.cmd.o.sampler_i),
			self.cmd.busy.eq(self.sampler.busy),

			# CMD -> RAM
			self.sample_ram.waddr.eq(self.cmd.o.ram_waddr),
			self.sample_ram.wdata.eq(self.cmd.o.ram_wdata),
			self.sample_ram.we   .eq(self.cmd.o.ram_we),

			# CMD -> Noise
			self.noise.i.eq(self.cmd.o.noise_i),
			self.noise.we.eq(self.cmd.o.noise_we),

			# CMD -> Mixer
			self.mixer.i.eq(self.cmd.o.mixer_i),
			self.mixer.we.eq(self.cmd.o.mixer_we),

			# Sampler <-> RAM
			self.sample_ram.raddr.eq(self.sampler.ram_addr),
			self.sampler.i.ram_data_0.eq(self.sample_ram.rdata_0),
			self.sampler.i.ram_data_1.eq(self.sample_ram.rdata_1),

			# Mixer -> PWM
			self.pwm.i.eq(self.mixer.o[:8]),

			# PWM -> Out
			self.o.eq(self.pwm.o),
		]

		if platform:
			m.d.comb += [
				# Pins -> UART
				self.uart.rx.eq(platform.request('uart').rx),

				# Sound -> THE WORLD
				platform.request('sound_out').pin.eq(self.o),
			]

		return m

# --------------------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------------------

def generate(top, *, do_program):
	from amaranth_boards.icestick import ICEStickPlatform

	platform = ICEStickPlatform()

	platform.add_resources([
		Resource('sound_out', 0,
			Subsignal('pin', Pins('3', conn=('j', 1), dir='o')),
		)
	])

	print('building...')
	platform.build(top, do_program = do_program)
	print('done.')

def filter_usage(input):
	lines = input.splitlines()
	output = []

	doing_cells = False

	for line in lines:
		if doing_cells:
			if line.strip() == '':
				doing_cells = False
			output.append(line)
		elif line.startswith('==='):
			output.append(line)
		elif line.strip().startswith('Number of cells'):
			output.append(line)
			doing_cells = True

	return '\n'.join(output)

def usage():
	import subprocess

	print('doing usage...')

	output = subprocess.run(['yosys',
		'-p', 'synth_ice40 -abc9 -noflatten',
		'build/top.debug.v'
	], check = True, capture_output = True, encoding = 'utf8').stdout

	print('done.')

	_, _, output = output.rpartition('Printing statistics.')
	output = filter_usage(output)

	with open('build/noflatten.rpt', 'wt') as f:
		f.write(output)

	subprocess.run(['subl', 'build/noflatten.rpt'])

def interactive():
	connect_over_serial('ftdi://ftdi:2232/2', baudrate = BAUDRATE)

def view():
	import subprocess

	subprocess.run(['nextpnr-ice40',
		'--pcf', 'build/top.pcf',
		'--json', 'build/top.json',
		'--gui', '--gui-no-aa',
		'--package', 'hx1k',
	])

def parse_args():
	parser = ArgumentParser()
	p_action = parser.add_subparsers(dest = 'action')
	p_action.add_parser('simulate')
	p_action.add_parser('usage')
	p_action.add_parser('connect')
	p_action.add_parser('view')

	p_generate = p_action.add_parser('generate')
	p_generate.add_argument('-p', '--program',
		help = 'program the device after generating',
		action = 'store_true')
	p_generate.add_argument('-i', '--interactive',
		help = 'connect over UART after programming',
		action = 'store_true')
	p_generate.add_argument('-v', '--view',
		help = 'view in nextpnr after generating',
		action = 'store_true')

	return parser.parse_args()

def make_top():
	top = Module()
	top.submodules.synth = synth = IcySynth(NUM_CHANNELS, SAMPLE_CYCS, BAUDRATE)
	return top

def main():
	args = parse_args()

	if args.action == 'simulate':
		top = make_top()
		simulate(top, top.submodules.synth)
	elif args.action == 'generate':
		generate(make_top(), do_program = args.interactive or args.program)

		if args.interactive:
			interactive()
		elif args.view:
			view()
	elif args.action == 'usage':
		usage()
	elif args.action == 'connect':
		interactive()
	elif args.action == 'view':
		view()
	else:
		print('wat?')

if __name__ == '__main__':
	main()
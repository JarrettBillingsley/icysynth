from argparse import ArgumentParser

from nmigen import *
from nmigen.build import Platform, Resource, Subsignal, Pins
from nmigen.back import verilog
from nmigen.back.pysim import *
from nmigen.hdl.rec import *

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

		self.ram     = SampleRam()
		self.sampler = Sampler(num_channels, sample_cycs)
		self.noise   = NoiseChannel()
		self.mixer   = Mixer(self.sampler.o, self.noise.o)
		self.pwm     = PWM()
		self.o       = Signal()
		pass

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# for simulation, set it to BAUDRATE * 5 so that it doesn't take
		# an age for each bit transition
		uart_freq = BAUDRATE * 5

		if platform:
			pll = PLL(platform.default_clk_frequency / 1_000_000, CLK_RATE / 1_000_000)
			# overrides the default 'sync' domain
			m.domains += pll.domain
			m.submodules.pll = pll
			m.d.comb += pll.clk_pin.eq(platform.request(platform.default_clk, dir='-'))

			uart_freq = int(pll.best_fout * 1_000_000)

		self.cmd = UartCmd(self.num_channels, self.mixer.bits_over_8, self.baudrate, uart_freq)

		m.submodules.cmd     = self.cmd
		m.submodules.ram     = self.ram
		m.submodules.sampler = self.sampler
		m.submodules.noise   = self.noise
		m.submodules.mixer   = self.mixer
		m.submodules.pwm     = self.pwm

		m.d.comb += [
			# CMD -> Sampler
			self.sampler.i.eq(self.cmd.o.sampler_i),

			# CMD -> RAM
			self.ram.waddr.eq(self.cmd.o.ram_waddr),
			self.ram.wdata.eq(self.cmd.o.ram_wdata),
			self.ram.we   .eq(self.cmd.o.ram_we),

			# Sampler <-> RAM
			self.ram.raddr.eq(self.sampler.ram_addr),
			self.sampler.i.ram_data.eq(self.ram.rdata),

			# CMD -> Noise
			self.noise.i.eq(self.cmd.o.noise_i),
			self.noise.we.eq(self.cmd.o.noise_we),

			# CMD -> Mixer
			self.mixer.i.eq(self.cmd.o.mixer_i),
			self.mixer.we.eq(self.cmd.o.mixer_we),

			# Mixer -> PWM
			self.pwm.i.eq(self.mixer.o[:8]),

			# PWM -> Out
			self.o.eq(self.pwm.o),
		]

		if platform:
			m.d.comb += [
				# Pins -> UART
				self.cmd.rx.eq(platform.request('uart').rx),

				# Sound -> THE WORLD
				platform.request('sound_out').pin.eq(self.o),
			]

		return m

# --------------------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------------------

def generate(top):
	from nmigen_boards.icestick import ICEStickPlatform

	platform = ICEStickPlatform()

	platform.add_resources([
		Resource('sound_out', 0,
			Subsignal('pin', Pins('3', conn=('j', 1), dir='o')),
		)
	])

	platform.build(top, do_program = args.program or args.interactive)

def interactive():
	connect_over_serial('ftdi://ftdi:2232/2', baudrate = BAUDRATE)

def view():
	import subprocess

	subprocess.run(['nextpnr-ice40',
		'--pcf', 'build/top.pcf',
		'--json', 'build/top.json',
		'--gui', '--gui-no-aa'
	])

def parse_args():
	parser = ArgumentParser()
	p_action = parser.add_subparsers(dest = 'action')
	p_action.add_parser('simulate')
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

if __name__ == '__main__':
	args = parse_args()

	top = Module()
	top.submodules.synth = synth = IcySynth(NUM_CHANNELS, SAMPLE_CYCS, BAUDRATE)

	if args.action == 'simulate':
		simulate(top, synth)
	elif args.action == 'generate':
		generate(top)

		if args.interactive:
			interactive()
		elif args.view:
			view()
	elif args.action == 'connect':
		interactive()
	elif args.action == 'view':
		view()
	else:
		print('wat?')
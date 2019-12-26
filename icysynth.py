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

def parse_args():
	parser = ArgumentParser()
	p_action = parser.add_subparsers(dest="action")
	p_action.add_parser("simulate")
	p_action.add_parser("generate")
	p_program = p_action.add_parser("program")
	p_program.add_argument('-i', '--interactive',
		help = 'connect over UART after programming',
		action = 'store_true')
	p_program.add_argument('-d', '--dry-run',
		help = 'build, but don\'t program',
		action = 'store_true')
	p_action.add_parser("connect")

	return parser.parse_args()

def interactive():
	connect_over_serial('ftdi://ftdi:2232/2', baudrate = BAUDRATE)

if __name__ == "__main__":
	top = Module()
	dut = IcySynth(NUM_CHANNELS, SAMPLE_CYCS, BAUDRATE)
	top.submodules.synth = dut
	args = parse_args()

	if args.action == "simulate":
		simulate(top, dut)
	elif args.action == "generate":
		v = verilog.convert(top, name = "top")

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

		platform.build(top, do_program = not args.dry_run)

		if args.interactive:
			interactive()
	elif args.action == "connect":
		interactive()
	else:
		print("wat?")
from argparse import ArgumentParser

from nmigen import *
from nmigen.build import Platform, Resource, Subsignal, Pins
from nmigen.back import verilog
from nmigen.back.pysim import *
from nmigen.hdl.rec import *

from mixer import *
from pll import *
from pwm import *
from ram import *
from serial_cmd import *
from sim import *
from term import connect_over_serial
from uart import *

# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------

# TODO: bodge (duplicated constants)
NUM_CHANNELS  = 4
CLK_RATE      = 16777216
SAMPLE_RATE   = 16384
SAMPLE_CYCS   = CLK_RATE // SAMPLE_RATE
CLK_PERIOD    = 1 / CLK_RATE
BAUDRATE      = 9600

# --------------------------------------------------------------------------------------------------
# The synth as a single module
# --------------------------------------------------------------------------------------------------

class IcySynth(Elaboratable):
	def __init__(self, num_channels: int, sample_cycs: int, baudrate: int):
		self.num_channels = num_channels
		self.baudrate = baudrate

		self.o     = Signal()
		self.mixer = Mixer(num_channels, sample_cycs)
		self.pwm   = PWM()
		self.ram   = SampleRam()
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

		m.submodules.mixer = self.mixer
		m.submodules.pwm   = self.pwm
		m.submodules.ram   = self.ram

		self.cmd = UartCmd(self.num_channels, self.baudrate, uart_freq)
		m.submodules.cmd   = self.cmd

		m.d.comb += [
			# CMD -> RAM
			self.ram.waddr.eq(self.cmd.o.ram_waddr),
			self.ram.wdata.eq(self.cmd.o.ram_wdata),
			self.ram.we.eq(self.cmd.o.ram_we),

			# CMD -> Mixer
			self.mixer.i.eq(self.cmd.o),

			# Mixer <-> RAM
			self.ram.raddr.eq(self.mixer.sample_ram_addr),
			self.mixer.sample_ram_data.eq(self.ram.rdata),

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
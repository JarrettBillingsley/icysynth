from argparse import ArgumentParser

from nmigen import *
from nmigen.build import Platform, Resource, Subsignal, Pins
from nmigen.back import verilog
from nmigen.back.pysim import *
from nmigen.hdl.rec import *

from pll import *
from uart import *
from mixer import *
from pwm import *
from ram import *
from sim import *
from term import connect_over_serial

# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------

NUM_CHANNELS  = 8
CLK_RATE      = 16777216
SAMPLE_RATE   = 16384
SAMPLE_CYCS   = CLK_RATE // SAMPLE_RATE
CLK_PERIOD    = 1 / CLK_RATE

# --------------------------------------------------------------------------------------------------
# The synth as a single module
# --------------------------------------------------------------------------------------------------

class IcySynth(Elaboratable):
	def __init__(self, num_channels: int, sample_cycs: int):
		self.o     = Signal()
		self.mixer = Mixer(num_channels, sample_cycs)
		self.pwm   = PWM()
		self.ram   = SampleRam()
		pass

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		if platform:
			pll = PLL(platform.default_clk_frequency / 1_000_000, CLK_RATE / 1_000_000)
			# overrides the default 'sync' domain
			m.domains += pll.domain
			m.submodules.pll = pll
			m.d.comb += pll.clk_pin.eq(platform.request(platform.default_clk, dir='-'))

		m.submodules.mixer = self.mixer
		m.submodules.pwm = self.pwm
		m.submodules.ram = self.ram

		m.d.comb += [
			self.ram.raddr.eq(self.mixer.sample_ram_addr),
			self.mixer.sample_ram_data.eq(self.ram.rdata),
			self.pwm.i.eq(self.mixer.o[:8]),
			self.o.eq(self.pwm.o),
		]

		if platform:
			m.d.comb += platform.request('sound_out').pin.eq(self.o)

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
	p_action.add_parser("connect")

	return parser.parse_args()

def interactive():
	connect_over_serial('ftdi://ftdi:2232:14:b/2', baudrate=9600)

if __name__ == "__main__":
	top = Module()
	dut = IcySynth(NUM_CHANNELS, SAMPLE_CYCS)
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

		platform.build(top, do_program=True)

		if args.interactive:
			interactive()
	elif args.action == "connect":
		interactive()
	else:
		print("wat?")
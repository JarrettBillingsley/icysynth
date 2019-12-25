from nmigen import *
from nmigen.back.pysim import *
from nmigen.build import Resource, Subsignal, Pins

# Dead simple super stupid SPI receiver.
class SPIReceiver(Elaboratable):
	def __init__(self, data_len):
		self.data_len = data_len

		# -------------------------------------
		# Inputs

		self.i_mosi = Signal()
		self.i_sclk = Signal()
		self.i_ssel = Signal(reset = 1)

		# -------------------------------------
		# Outputs

		self.o_data = Signal(data_len)
		self.o_done = Signal(reset = 1)

	def elaborate(self, platform):
		m = Module()

		if not platform:
			# BUG: workaround for nmigen not including input signals in VCD traces
			mosi = Signal(name='i_mosi')
			sclk = Signal(name='i_sclk')
			ssel = Signal(name='i_ssel')
			m.d.comb += [mosi.eq(self.i_mosi), sclk.eq(self.i_sclk), ssel.eq(self.i_ssel)]

		sclk_latch = Signal()
		sclk_edge  = Signal()
		m.d.sync += sclk_latch.eq(self.i_sclk)
		m.d.comb += sclk_edge.eq((self.i_sclk) & ~(sclk_latch))

		with m.FSM(name = 'spi_fsm'):
			with m.State('IDLE'):
				with m.If(self.i_ssel == 0):
					m.d.sync += self.o_done.eq(0)
					m.next = 'RECV'

			with m.State('RECV'):
				with m.If(sclk_edge):
					m.d.sync += self.o_data.eq(Cat(self.o_data[1:], self.i_mosi))
				with m.Elif(self.i_ssel == 1):
					m.d.sync += self.o_done.eq(1)
					m.next = 'IDLE'

		return m

def transfer(spi, length, val):
	for i in range(length):
		yield spi.i_mosi.eq(val & 1)
		yield spi.i_sclk.eq(1)
		yield
		yield spi.i_sclk.eq(0)
		yield
		yield
		yield
		val >>= 1

def delay(n):
    return [None] * n

def test(top):
	spi = top.submodules.spi

	yield spi.i_ssel.eq(1)
	yield from delay(3)

	yield spi.i_ssel.eq(0)
	yield
	yield from transfer(spi, 8, 0xA5)
	yield spi.i_ssel.eq(1)
	yield

def build(top):
	from nmigen_boards.icestick import ICEStickPlatform
	platform = ICEStickPlatform()
	platform.add_resources([
		Resource("spi", 0,
			Subsignal("mosi", Pins('3', conn=('j', 1), dir='i')),
			Subsignal("sclk", Pins('4', conn=('j', 1), dir='i')),
			Subsignal("ssel", Pins('5', conn=('j', 1), dir='i')),
		)
	])

	conn = platform.request('spi')
	spi = top.submodules.spi

	top.d.comb += [
		spi.i_mosi.eq(conn.mosi),
		spi.i_sclk.eq(conn.sclk),
		spi.i_ssel.eq(conn.ssel),
		platform.request('led', 4).eq(spi.o_done),
		platform.request('led', 0).eq(spi.o_data[0]),
	]

	platform.build(top, do_program = False)

def sim(top):
	sim = Simulator(top)
	sim.add_clock(1e-6)
	def shim():
		yield from test(top)
	sim.add_sync_process(shim)

	with sim.write_vcd("spi.vcd"):
		sim.run_until(1e-6 * 300, run_passive = True)

if __name__ == "__main__":
	top = Module()
	top.submodules.spi = SPIReceiver(8)

	build(top)
	# sim(top)
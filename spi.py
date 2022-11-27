from amaranth import *
from amaranth.sim import *
from amaranth.build import Resource, Subsignal, Pins

class XDomainLatch(Elaboratable):
	def __init__(self):
		super().__init__()
		self.i       = Signal()
		self.rising  = Signal()
		self.falling = Signal()

	def elaborate(self, platform):
		m = Module()

		latch = Signal(3)
		m.d.sync += latch.eq(Cat(self.i, latch[:2]))
		m.d.comb += self.rising.eq(latch[1:] == 0b01)
		m.d.comb += self.falling.eq(latch[1:] == 0b10)

		return m

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
			# BUG: workaround for amaranth not including input signals in VCD traces
			mosi = Signal(name='i_mosi')
			sclk = Signal(name='i_sclk')
			ssel = Signal(name='i_ssel')
			m.d.comb += [mosi.eq(self.i_mosi), sclk.eq(self.i_sclk), ssel.eq(self.i_ssel)]

		# Latches for SCLK and SSEL (three-stage to reliably sample across clock domains)
		sclk = XDomainLatch()
		ssel = XDomainLatch()
		m.submodules.sclk_latch = sclk
		m.submodules.ssel_latch = ssel
		m.d.comb += sclk.i.eq(self.i_sclk)
		m.d.comb += ssel.i.eq(self.i_ssel)

		# Latch for MOSI
		mosi_latch = Signal(2)
		m.d.sync += mosi_latch.eq(Cat(self.i_mosi, mosi_latch[0]))
		mosi = mosi_latch[1]

		with m.FSM(name = 'spi_fsm'):
			with m.State('IDLE'):
				with m.If(ssel.falling):
					m.d.sync += self.o_done.eq(0)
					m.next = 'RECV'

			with m.State('RECV'):
				with m.If(sclk.rising):
					m.d.sync += self.o_data.eq(Cat(self.o_data[1:], mosi))
				with m.Elif(ssel.rising):
					m.d.sync += self.o_done.eq(1)
					m.next = 'IDLE'

		return m

def transfer(spi, length, val):
	yield spi.i_ssel.eq(0)
	yield

	for i in range(length):
		yield spi.i_mosi.eq(val & 1)
		yield spi.i_sclk.eq(1)
		yield
		yield spi.i_sclk.eq(0)
		yield
		val >>= 1
	yield spi.i_ssel.eq(1)

def delay(n):
    return [None] * n

def test(top):
	spi = top.submodules.spi

	# yield spi.i_ssel.eq(1)
	yield from delay(3)
	yield from transfer(spi, 32, 0xDEADBEEF)

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

CLK_PERIOD = 1 / 16777216

def sim(top):
	sim = Simulator(top)
	sim.add_clock(CLK_PERIOD)
	def shim():
		yield from test(top)
	sim.add_sync_process(shim)

	with sim.write_vcd("spi.vcd"):
		sim.run_until(CLK_PERIOD * 300, run_passive = True)

if __name__ == "__main__":
	top = Module()
	top.submodules.spi = SPIReceiver(32)

	# build(top)
	sim(top)
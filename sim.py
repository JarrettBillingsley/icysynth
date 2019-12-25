from nmigen import *
from nmigen.build import Platform
from nmigen.back.pysim import *

# TODO: bodge (duplicated constants)
NUM_CHANNELS  = 8
CLK_RATE      = 16777216
SAMPLE_RATE   = 16384
SAMPLE_CYCS   = CLK_RATE // SAMPLE_RATE
CLK_PERIOD    = 1 / CLK_RATE

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
	yield mix.i.chan_select.eq(i)
	yield mix.i.chan_inputs.rate.eq(values['rate'])
	yield mix.i.chan_inputs.length.eq(values['length'])
	yield mix.i.chan_inputs.start.eq(values['start'])
	yield mix.i.chan_inputs.vol.eq(values['vol'])
	yield from toggle_enable(mix.i.chan_we.rate, mix.i.chan_we.sample, mix.i.chan_we.vol)

def delay(n):
    return [None] * n

def test_proc(mix):
	# setup channels
	for i in range(NUM_CHANNELS):
		yield from setup_channel(mix, i, CHANNEL_INIT_VALUES[i])

	yield mix.i.noise_inputs.vol.eq(3)
	yield mix.i.noise_inputs.period.eq(50)
	yield from toggle_enable(mix.i.noise_we.vol, mix.i.noise_we.period)

	# setup mixer state
	yield mix.i.inputs.chan_enable.eq(0x0F)
	yield mix.i.inputs.mix_shift.eq(0)
	yield from toggle_enable(mix.i.we.chan_enable, mix.i.we.mix_shift)

def serial_send(rx, divisor, data):
	yield rx.eq(1)
	yield from delay(3)

	# start bit
	yield rx.eq(0)
	yield from delay(divisor)

	# data bits
	for i in range(8):
		yield rx.eq((data >> i) & 1)
		yield from delay(divisor)

	# stop bit
	yield rx.eq(1)
	yield from delay(divisor + 2)


def test_proc2(cmd):
	d = cmd.uart_rx.divisor
	yield from delay(2)
	yield from serial_send(cmd.rx, d, ord('1'))
	yield from serial_send(cmd.rx, d, ord('2'))
	yield from serial_send(cmd.rx, d, ord('3'))

SIM_CLOCKS = 5000

def simulate(top, dut):
	sim = Simulator(top)
	sim.add_clock(CLK_PERIOD)

	def fuckyou():
		yield from test_proc(dut.mixer)
		# yield from test_proc2(dut.cmd)
	sim.add_sync_process(fuckyou)

	# BUG: nmigen currently ignores the 'traces' param on this function,
	# so the resulting gtkw isn't very useful.
	with sim.write_vcd("out.vcd"):
		sim.run_until(CLK_PERIOD * SIM_CLOCKS, run_passive = True)

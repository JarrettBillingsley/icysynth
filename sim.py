from amaranth import *
from amaranth.build import Platform
from amaranth.back.pysim import *

from constants import *

# --------------------------------------------------------------------------------------------------
# Testing
# --------------------------------------------------------------------------------------------------

def toggle_enable(*sig):
	for s in sig:
		yield s.eq(1)
	yield

	for s in sig:
		yield s.eq(0)

def setup_channel(samp, i, values):
	yield samp.i.chan_select.eq(i)
	yield samp.i.chan_i.rate.eq(values['rate'])
	yield samp.i.chan_i.length.eq(values['length'])
	yield samp.i.chan_i.start.eq(values['start'])
	yield samp.i.chan_i.vol.eq(values['vol'])
	yield from toggle_enable(samp.i.chan_we.rate, samp.i.chan_we.sample, samp.i.chan_we.vol)

def delay(n):
    return [None] * n

def test_setup_synth(synth):
	mix = synth.mixer
	samp = synth.sampler
	noise = synth.noise

	# setup channels
	for i in range(NUM_CHANNELS):
		yield from setup_channel(samp, i, CHANNEL_INIT_VALUES[i])

	yield noise.i.vol.eq(3)
	yield noise.i.period.eq(1)
	yield from toggle_enable(noise.we.vol, noise.we.period)

	# setup mixer state
	yield samp.i.chan_enable.eq(0x0F)
	yield mix.i.mix_shift.eq(3)
	yield from toggle_enable(samp.i.chan_enable_we, mix.we.mix_shift)

def serial_send(uart, data):
	rx = uart.rx
	divisor = uart.uart.divisor

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

def wait_for(signal, value = 1):
	while (yield signal) != value:
		yield

def serial_cmd(uart, op, a0 = 0, a1 = 0, a2 = 0):
	yield from wait_for(uart.cts, 1)
	yield from serial_send(uart, op)
	yield from serial_send(uart, a0)
	yield from serial_send(uart, a1)
	yield from serial_send(uart, a2)
	yield from wait_for(uart.cts, 0)
	yield from wait_for(uart.cts, 1)

def test_serial(uart):
	yield from serial_cmd(uart, 0)
	yield from serial_cmd(uart, 1)
	yield from serial_cmd(uart, 0x80, 0x12, 0x34, 0x56)

def simulate(top, synth):
	sim = Simulator(top)
	sim.add_clock(CLK_PERIOD)

	def shim():
		# yield from test_setup_synth(synth)
		# yield from test_serial(synth.uart)
		yield
	sim.add_sync_process(shim)

	# BUG: amaranth currently ignores the 'traces' param on this function,
	# so the resulting gtkw isn't very useful.
	with sim.write_vcd("out.vcd"):
		sim.run_until(CLK_PERIOD * SIM_CLOCKS, run_passive = True)

from nmigen import *
from nmigen.build import Platform
from nmigen.back.pysim import *

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
	yield samp.i.chan_inputs.rate.eq(values['rate'])
	yield samp.i.chan_inputs.length.eq(values['length'])
	yield samp.i.chan_inputs.start.eq(values['start'])
	yield samp.i.chan_inputs.vol.eq(values['vol'])
	yield from toggle_enable(samp.i.chan_we.rate, samp.i.chan_we.sample, samp.i.chan_we.vol)

def delay(n):
    return [None] * n

def test_proc(synth):
	mix = synth.mixer
	samp = synth.sampler
	noise = synth.noise

	# setup channels
	for i in range(NUM_CHANNELS):
		yield from setup_channel(samp, i, CHANNEL_INIT_VALUES[i])

	yield noise.i.vol.eq(3)
	yield noise.i.period.eq(50)
	yield from toggle_enable(noise.we.vol, noise.we.period)

	# setup mixer state
	yield samp.i.chan_enable.eq(0x0F)
	yield mix.i.mix_shift.eq(3)
	yield from toggle_enable(samp.i.chan_enable_we, mix.we.mix_shift)

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
	d = cmd.uart.divisor
	yield from delay(2)
	yield from serial_send(cmd.rx, d, ord('1'))
	yield from serial_send(cmd.rx, d, ord('2'))
	yield from serial_send(cmd.rx, d, ord('3'))

SIM_CLOCKS = 5000

def simulate(top, synth):
	sim = Simulator(top)
	sim.add_clock(CLK_PERIOD)

	def fuckyou():
		yield from test_proc(synth)
		yield from test_proc2(synth.cmd)
	sim.add_sync_process(fuckyou)

	# BUG: nmigen currently ignores the 'traces' param on this function,
	# so the resulting gtkw isn't very useful.
	with sim.write_vcd("out.vcd"):
		sim.run_until(CLK_PERIOD * SIM_CLOCKS, run_passive = True)

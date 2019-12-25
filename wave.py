from nmigen import *
from nmigen.build import Platform

from signals import *

# TODO: bodge
from sim import *

# --------------------------------------------------------------------------------------------------
# Wave Channel
# --------------------------------------------------------------------------------------------------

class WaveChannel(Elaboratable):
	def __init__(self, i):
		self.index = i

		# -------------------------------------
		# Inputs

		self.inputs      = WaveState()
		self.we          = WaveEnable()
		self.commit      = Signal()
		self.enabled     = Signal()

		# -------------------------------------
		# Outputs

		self.sample_addr = Signal(9)
		self.sample_vol  = Signal(4)

		# -------------------------------------
		# Juicy Internals

		self.internal_state = WaveState(name = 'real')

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# -------------------------------------
		# Internal State

		phase_dirty = Signal(1)
		shadow      = WaveState(name='shadow')
		state       = self.internal_state

		if platform:
			shadow.rate.reset   = CHANNEL_INIT_VALUES[self.index]['rate']
			shadow.length.reset = CHANNEL_INIT_VALUES[self.index]['length']
			shadow.start.reset  = CHANNEL_INIT_VALUES[self.index]['start']
			shadow.vol.reset    = CHANNEL_INIT_VALUES[self.index]['vol']
			state.rate.reset   = CHANNEL_INIT_VALUES[self.index]['rate']
			state.length.reset = CHANNEL_INIT_VALUES[self.index]['length']
			state.start.reset  = CHANNEL_INIT_VALUES[self.index]['start']
			state.vol.reset    = CHANNEL_INIT_VALUES[self.index]['vol']

		# -------------------------------------
		# Combinational Logic

		m.d.comb += [
			self.sample_addr.eq((state.phase[-9:] & state.length) + state.start),
			self.sample_vol.eq(state.vol),
		]

		# -------------------------------------
		# Sequential Logic

		# Processing
		# with m.If(self.enabled):
			# m.d.sync += state.phase.eq((state.phase + state.rate)[0:24])

		# Writing to shadow state
		with m.If(self.we.phase):
			m.d.sync += [
				shadow.phase.eq(self.inputs.phase),
				phase_dirty.eq(1),
			]
		with m.If(self.we.rate):
			m.d.sync += shadow.rate.eq(self.inputs.rate)
		with m.If(self.we.sample):
			m.d.sync += [
				shadow.start.eq(self.inputs.start),
				shadow.length.eq(self.inputs.length),
			]
		with m.If(self.we.vol):
			m.d.sync += shadow.vol.eq(self.inputs.vol)

		# Committing shadow state to real state
		with m.If(self.commit):
			m.d.sync += [
				state.rate.  eq(shadow.rate  ),
				state.start. eq(shadow.start ),
				state.length.eq(shadow.length),
				state.vol.   eq(shadow.vol   ),
			]

			with m.If(phase_dirty):
				m.d.sync += [
					# state.phase.eq(shadow.phase), TODO: temp
					phase_dirty.eq(0),
				]

		return m

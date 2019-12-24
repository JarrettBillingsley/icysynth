from nmigen import *
from nmigen.hdl.rec import *

class MixerStateLayout(Layout):
	def __init__(self, num_channels):
		super().__init__([
			('chan_enable',  num_channels),
			('mix_shift',    2),
		])

class MixerState(Record):
	def __init__(self, num_channels, name=None):
		super().__init__(MixerStateLayout(num_channels), name=name)

class MixerEnable(Record):
	def __init__(self):
		super().__init__([
			('chan_enable', 1),
			('mix_shift',   1),
		])

class NoiseState(Record):
	def __init__(self, name=None):
		super().__init__([
			('period', 16),
			('vol',    4),
		], name=name)

class NoiseEnable(Record):
	def __init__(self):
		super().__init__([
			('period', 1),
			('vol',    1),
		])

class WaveState(Record):
	def __init__(self, name=None):
		super().__init__([
			('phase',  24),
			('rate',   24),
			('start',  9),
			('length', 9),
			('vol',    4),
		], name=name)

class WaveEnable(Record):
	def __init__(self):
		super().__init__([
			('phase',  1),
			('rate',   1),
			('sample', 1),
			('vol',    1),
		])

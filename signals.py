from nmigen import *
from nmigen.hdl.rec import *

# ALL THIS BOILERPLAAAAAATE AAAAAAAAAAGHHHHHHHHHHGHHGHH

# --------------------------------------------------------------------------------------------------
# Layouts
# --------------------------------------------------------------------------------------------------

class MixerStateLayout(Layout):
	def __init__(self, num_channels): super().__init__([
			('chan_enable',  num_channels),
			('mix_shift',    2),
		])

class MixerEnableLayout(Layout):
	def __init__(self): super().__init__([
			('chan_enable', 1),
			('mix_shift',   1),
		])

class MixerInputLayout(Layout):
	def __init__(self, num_channels): super().__init__([
			('inputs',       MixerStateLayout(num_channels)),
			('we',           MixerEnableLayout()           ),
			('commit',       1                             ),
			('chan_select',  range(num_channels)           ),
			('chan_inputs',  WaveStateLayout()             ),
			('chan_we',      WaveEnableLayout()            ),
			('noise_inputs', NoiseStateLayout()            ),
			('noise_we',     NoiseEnableLayout()           ),
		])

class WaveStateLayout(Layout):
	def __init__(self): super().__init__([
			('phase',  24),
			('rate',   24),
			('start',  9),
			('length', 9),
			('vol',    4),
		])

class WaveEnableLayout(Layout):
	def __init__(self): super().__init__([
			('phase',  1),
			('rate',   1),
			('sample', 1),
			('vol',    1),
		])

class NoiseStateLayout(Layout):
	def __init__(self): super().__init__([
			('period', 16),
			('vol',    4),
		])

class NoiseEnableLayout(Layout):
	def __init__(self): super().__init__([
			('period', 1),
			('vol',    1),
		])

class CommandOutputLayout(Layout):
	def __init__(self, num_channels): super().__init__([
			('mixer_i',   MixerInputLayout(num_channels)),
			('ram_waddr', 9),
			('ram_wdata', 4),
			('ram_we',    1),
		])

# --------------------------------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------------------------------

class MixerState(Record):
	def __init__(self, n, name=None): super().__init__(MixerStateLayout(n), name=name)
class MixerEnable(Record):
	def __init__(self): super().__init__(MixerEnableLayout())

class NoiseState(Record):
	def __init__(self, name=None):    super().__init__(NoiseStateLayout(), name=name)
class NoiseEnable(Record):
	def __init__(self): super().__init__(NoiseEnableLayout())

class WaveState(Record):
	def __init__(self, name=None):    super().__init__(WaveStateLayout(), name=name)
class WaveEnable(Record):
	def __init__(self): super().__init__(WaveEnableLayout())

class MixerInput(Record):
	def __init__(self, n): super().__init__(MixerInputLayout(n))

class CommandOutput(Record):
	def __init__(self, n): super().__init__(CommandOutputLayout(n))
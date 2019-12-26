from nmigen import *
from nmigen.hdl.rec import *

# ALL THIS BOILERPLAAAAAATE AAAAAAAAAAGHHHHHHHHHHGHHGHH

# --------------------------------------------------------------------------------------------------
# Layouts
# --------------------------------------------------------------------------------------------------

class MixerStateLayout(Layout):
	def __init__(self, bits_over_8): super().__init__([
			('mix_shift', bits_over_8),
		])

class MixerEnableLayout(Layout):
	def __init__(self): super().__init__([
			('mix_shift', 1),
		])

class SamplerInputLayout(Layout):
	def __init__(self, num_channels): super().__init__([
			('chan_enable',    num_channels       ),
			('chan_enable_we', 1                  ),
			('chan_select',    range(num_channels)),
			('chan_inputs',    WaveStateLayout()  ),
			('chan_we',        WaveEnableLayout() ),
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
	def __init__(self, num_channels, bits_over_8): super().__init__([
			('sampler_i', SamplerInputLayout(num_channels)),
			('noise_i',   NoiseStateLayout()),
			('noise_we',  NoiseEnableLayout()),
			('mixer_i',   MixerStateLayout(bits_over_8)),
			('mixer_we',  MixerEnableLayout()),
			('ram_waddr', 9),
			('ram_wdata', 4),
			('ram_we',    1),
		])

# --------------------------------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------------------------------

class NoiseState(Record):
	def __init__(self, name=None):    super().__init__(NoiseStateLayout(), name=name)
class NoiseEnable(Record):
	def __init__(self): super().__init__(NoiseEnableLayout())

class WaveState(Record):
	def __init__(self, name=None):    super().__init__(WaveStateLayout(), name=name)
class WaveEnable(Record):
	def __init__(self): super().__init__(WaveEnableLayout())

class SamplerInput(Record):
	def __init__(self, n): super().__init__(SamplerInputLayout(n))

class MixerState(Record):
	def __init__(self, n): super().__init__(MixerStateLayout(n))
class MixerEnable(Record):
	def __init__(self): super().__init__(MixerEnableLayout())

class CommandOutput(Record):
	def __init__(self, n, b): super().__init__(CommandOutputLayout(n, b))
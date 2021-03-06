
# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------

SIM_CLOCKS       = 8000
TESTING          = True

NUM_CHANNELS     = 8
CLK_RATE         = 16777216
SAMPLE_RATE      = 16384
SAMPLE_CYCS      = CLK_RATE // SAMPLE_RATE
CLK_PERIOD       = 1 / CLK_RATE
BAUDRATE         = 38400
SAMPLE_ADDR_BITS = 9
SAMPLE_BITS      = 4
VOL_BITS         = 4
PHASE_BITS       = 24

CHANNEL_INIT_VALUES = [
	{ 'rate': 0x008000, 'length': 0x3F, 'start': 0x00, 'vol': 0x0F }, # 0
	{ 'rate': 0x00C000, 'length': 0x3F, 'start': 0x00, 'vol': 0x0F }, # 1
	{ 'rate': 0x012000, 'length': 0x3F, 'start': 0x00, 'vol': 0x0F }, # 2
	{ 'rate': 0x024000, 'length': 0x3F, 'start': 0x00, 'vol': 0x0F }, # 3
	{ 'rate': 0x003000, 'length': 0x3F, 'start': 0x40, 'vol': 0x0F }, # 4
	{ 'rate': 0x004800, 'length': 0x3F, 'start': 0x40, 'vol': 0x0F }, # 5
	{ 'rate': 0x006C00, 'length': 0x3F, 'start': 0x40, 'vol': 0x0F }, # 6
	{ 'rate': 0x00D800, 'length': 0x3F, 'start': 0x40, 'vol': 0x0F }, # 7
]

DUMMY_RAM = [
	# sine
	0x8, 0x8, 0x9, 0xA, 0xB, 0xB, 0xC, 0xD, 0xD, 0xE, 0xE, 0xF, 0xF, 0xF, 0xF, 0xF,
	0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xE, 0xE, 0xD, 0xD, 0xC, 0xB, 0xB, 0xA, 0x9, 0x8,
	0x8, 0x7, 0x6, 0x5, 0x4, 0x4, 0x3, 0x2, 0x2, 0x1, 0x1, 0x1, 0x0, 0x0, 0x0, 0x0,
	0x0, 0x0, 0x0, 0x0, 0x0, 0x1, 0x1, 0x1, 0x2, 0x2, 0x3, 0x4, 0x4, 0x5, 0x6, 0x7,

	# saw
	0x0, 0x0, 0x0, 0x0, 0x1, 0x1, 0x1, 0x1, 0x2, 0x2, 0x2, 0x2, 0x3, 0x3, 0x3, 0x3,
	0x4, 0x4, 0x4, 0x4, 0x5, 0x5, 0x5, 0x5, 0x6, 0x6, 0x6, 0x6, 0x7, 0x7, 0x7, 0x7,
	0x8, 0x8, 0x8, 0x8, 0x9, 0x9, 0x9, 0x9, 0xA, 0xA, 0xA, 0xA, 0xB, 0xB, 0xB, 0xB,
	0xC, 0xC, 0xC, 0xC, 0xD, 0xD, 0xD, 0xD, 0xE, 0xE, 0xE, 0xE, 0xF, 0xF, 0xF, 0xF,

	# tri
	0x0, 0x0, 0x1, 0x1, 0x2, 0x2, 0x3, 0x3, 0x4, 0x4, 0x5, 0x5, 0x6, 0x6, 0x7, 0x7,
	0x8, 0x8, 0x9, 0x9, 0xA, 0xA, 0xB, 0xB, 0xC, 0xC, 0xD, 0xD, 0xE, 0xE, 0xF, 0xF,
	0xF, 0xF, 0xE, 0xE, 0xD, 0xD, 0xC, 0xC, 0xB, 0xB, 0xA, 0xA, 0x9, 0x9, 0x8, 0x8,
	0x7, 0x7, 0x6, 0x6, 0x5, 0x5, 0x4, 0x4, 0x3, 0x3, 0x2, 0x2, 0x1, 0x1, 0x0, 0x0,

	# square
	0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
	0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
	0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF,
	0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF, 0xF,
] + [0] * 256
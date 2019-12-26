
# --------------------------------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------------------------------

NUM_CHANNELS  = 8
CLK_RATE      = 16777216
SAMPLE_RATE   = 16384
SAMPLE_CYCS   = CLK_RATE // SAMPLE_RATE
CLK_PERIOD    = 1 / CLK_RATE
BAUDRATE      = 9600

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
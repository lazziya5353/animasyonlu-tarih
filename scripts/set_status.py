import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import set_status
set_status(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)

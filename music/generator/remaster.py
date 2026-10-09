import sys, os
import soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth import master, SR
src, dst = sys.argv[1], sys.argv[2]
x, sr = sf.read(src, always_2d=True)
assert sr == SR
y = master(x.T, -10.0, -2.2)
sf.write(dst, y.T, SR, subtype='PCM_24')

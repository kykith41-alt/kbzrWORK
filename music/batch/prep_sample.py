# Clean up the user's 0.9 s clip: remove rumble, smooth the cut-off ending by
# "freezing" its last slice into a natural decay, and render a version with echo.
import numpy as np, soundfile as sf, sys, librosa
from scipy.signal import butter, sosfilt, fftconvolve
SR=44100
def flt(x,kind,fc,o=2): return sosfilt(butter(o,fc,kind,fs=SR,output='sos'),x,axis=0)
y,_=librosa.load(sys.argv[1],sr=SR,mono=False)
y=np.atleast_2d(y).T if y.ndim==1 else y.T            # (n,2)
if y.shape[1]==1: y=np.repeat(y,2,1)
y=flt(y,'high',90,4)                                  # remove low rumble
y=y/np.abs(y).max()*0.9
n=len(y); fi=int(0.006*SR); y[:fi]*=np.linspace(0,1,fi)[:,None]
# freeze-extend: overlap-add hann grains taken from the last 180 ms, decaying over 0.9 s
src=y[-int(0.18*SR):]; g=int(0.09*SR); hop=g//2; win=np.hanning(g)[:,None]
ext_len=int(0.9*SR); ext=np.zeros((ext_len+g,2)); rng=np.random.default_rng(1)
for k,pos in enumerate(range(0,ext_len,hop)):
    st=rng.integers(0,len(src)-g); amp=np.exp(-pos/SR*4.0)
    ext[pos:pos+g]+=src[st:st+g]*win*amp
ext=flt(ext,'low',3500,2)
# crossfade original end into the extension
xf=int(0.06*SR); out=np.concatenate([y,np.zeros((len(ext),2))])
out[n-xf:n]*=np.linspace(1,0,xf)[:,None]**0.5
out[n-xf:n-xf+len(ext)]+=ext*np.concatenate([np.linspace(0,1,xf)**0.5,np.ones(len(ext)-xf)])[:,None]
out=out[:n-xf+ext_len]; fo=int(0.25*SR); out[-fo:]*=np.linspace(1,0,fo)[:,None]**2
sf.write(sys.argv[2],out.astype(np.float32),SR)
# standalone version with echo + reverb (dotted-8th at 124 BPM, ping-pong)
BEAT=60/124; D=int(BEAT*0.75*SR); fb=0.5
tail=np.zeros((len(out)+D*8+SR*3,2)); tail[:len(out)]+=out
for i in range(1,8):
    e=flt(out,'low',max(4000-i*400,1200),2)*fb**i
    e=e[:, ::-1] if i%2 else e
    tail[D*i:D*i+len(out)]+=e
t=np.arange(int(2.5*SR))/SR; ir=np.stack([flt(rng.standard_normal(len(t)),'low',4000)*np.exp(-t*2.8) for _ in range(2)],1)
wet=np.stack([fftconvolve(tail[:,c],ir[:,c])[:len(tail)] for c in range(2)],1); wet*=0.35/np.sqrt((ir**2).sum()/2)
res=tail+wet; res/=np.abs(res).max()/0.9
sf.write(sys.argv[3],res.astype(np.float32),SR)
print('clean',round(len(out)/SR,2),'s   echo',round(len(res)/SR,2),'s')

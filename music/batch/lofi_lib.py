# Shared instruments for the lo-fi batch (from v7).
import numpy as np, soundfile as sf, sys
from scipy.signal import butter, sosfilt, fftconvolve
SR=44100; BPM=120; BEAT=60/BPM; BAR=4*BEAT; S16=BEAT/4
rng=np.random.default_rng(5)
def m2f(m): return 440*2**((m-69)/12)
def flt(x,kind,fc,o=2): return sosfilt(butter(o,fc,kind,fs=SR,output='sos'),x,axis=0)
def lp(x,fc,o=2): return flt(x,'low',min(fc,SR*0.45),o)
def hp(x,fc,o=2): return flt(x,'high',fc,o)
def bp(x,lo,hi,o=2): return flt(x,'band',[lo,min(hi,SR*0.45)],o)

rng=np.random.default_rng(0)
def phase(f): return np.cumsum(f)/SR
def pulse(ph,w=0.4): return np.where((ph%1)<w,1.0,-1.0)
def saw(ph): return 2*(ph%1)-1
# ---------- instruments
def organ(ms,dur):
    """reedy, accordion/organ-like chord with slow beating"""
    n=int(dur*SR); t=np.arange(n)/SR; s=np.zeros(n)
    for m in ms:
        for d in (-0.09,0.08):
            f=m2f(m)*2**(d/12)*(1+0.002*np.sin(2*np.pi*(0.4+rng.random())*t)+0.004*np.sin(2*np.pi*4.6*t))
            ph=phase(f)+rng.random()
            s+=0.6*pulse(ph,0.3+0.1*np.sin(2*np.pi*0.7*t))+0.4*saw(ph)
    s=lp(s,2200,2)/(len(ms)*2)
    e=np.minimum(t/0.03,1)*np.clip((dur-t)/0.05,0,1)*(0.85+0.15*np.exp(-t*3))
    return s*e*0.32
def bassline(m,dur):
    n=int(dur*SR); t=np.arange(n)/SR; ph=phase(np.full(n,m2f(m)))
    s=lp(saw(ph)+0.5*pulse(ph,0.5),700)
    return np.tanh(2*s)*np.minimum(t/0.01,1)*np.clip((dur-t)/0.03,0,1)*np.exp(-t*0.8)*0.4
def lead(notes,T):
    """warbly lead with portamento, heavy vibrato and end-of-phrase dives"""
    n=int(T*SR); f=np.zeros(n); a=np.zeros(n); t=np.arange(n)/SR; cur=m2f(notes[0][1])
    for s,m,l,dive in notes:
        i0=int(s*SR); i1=min(int((s+l)*SR),n); tgt=m2f(m); L=i1-i0
        seg=np.full(L,tgt); g=min(int(0.07*SR),L); seg[:g]=cur*(tgt/cur)**(np.linspace(0,1,g)**0.5)
        if dive:   # pitch dive at the tail
            dl=min(int(0.3*SR),L); seg[-dl:]*=2**(np.linspace(0,dive,dl)**2/12* (1 if dive>0 else -1)*np.sign(dive)) if False else 2**(dive*np.linspace(0,1,dl)**2/12)
        f[i0:i1]=seg; cur=seg[-1]
        k=np.arange(L)/SR; a[i0:i1]=np.maximum(a[i0:i1],np.minimum(k/0.03,1)*np.clip((l-k)/0.06,0,1))
    idx=np.where(f>0,np.arange(n),0); np.maximum.accumulate(idx,out=idx); f=f[idx]; f[f==0]=m2f(notes[0][1])
    vib=1+0.026*np.sin(2*np.pi*5.0*t+0.4*np.sin(2*np.pi*0.3*t))*np.clip(a,0,1)
    ph=phase(f*vib)
    s=0.55*saw(ph)+0.45*pulse(ph*1.003+0.2,0.45)
    return np.tanh(1.6*lp(s,2400))*a*0.3
def drop(f0=330,f1=55,dur=0.45):
    n=int(dur*SR); t=np.arange(n)/SR; f=f0*(f1/f0)**((t/dur)**0.6)
    return lp(saw(phase(f)),1800)*np.exp(-t*4)*0.35
def kick():
    n=int(0.25*SR); t=np.arange(n)/SR
    s=np.sin(2*np.pi*phase(85+110*np.exp(-t*40)))*np.exp(-t*16)
    return np.tanh(2*s)*0.7
def snare():
    n=int(0.3*SR); t=np.arange(n)/SR
    return (lp(bp(rng.standard_normal(n),700,3500),3500)*np.exp(-t*15)+np.sin(2*np.pi*220*t)*np.exp(-t*30)*0.4)*0.55
def hat(v=1):
    n=int(0.05*SR); t=np.arange(n)/SR; return bp(rng.standard_normal(n),3500,6000)*np.exp(-t*80)*0.12*v

def ks(m,dur,t60=1.8,bright=0.5):
    f=m2f(m); P=int(round(SR/f)); n=int(dur*SR)
    dec=np.exp(np.log(0.001)/(f*t60)); y=np.zeros(n+P)
    exc=lp(rng.uniform(-1,1,P),1200+bright*5000); y[:P]=exc-np.roll(exc,P//4)*0.5
    for st in range(P,n,P):
        e=min(st+P,n); pr=y[st-P:e-P+1]
        y[st:e]=dec*0.5*(pr[:e-st]+np.append(pr[1:],0)[:e-st])
    o=bp(y[:n],100,3500); o[-600:]*=np.linspace(1,0,600); return o*0.55
def choir(ms,dur):
    n=int(dur*SR); t=np.arange(n)/SR; s=np.zeros(n)
    for m in ms:
        for d in (-0.13,0.0,0.11):
            vib=1+0.005*np.sin(2*np.pi*(4.8+rng.random())*t+rng.random()*6)
            s+=np.tanh(1.4*np.sin(2*np.pi*phase(m2f(m)*2**(d/12)*vib)))
    s=bp(s,500,1000)+0.6*bp(s,1000,1400)+0.3*bp(s,2400,2900)   # 'aa' formants
    return s/(len(ms)*3)*np.minimum(t/0.7,1)*np.clip((dur-t)/0.5,0,1)*0.55
def bell(m,dur=1.5):
    n=int(dur*SR); t=np.arange(n)/SR; f=m2f(m)
    return np.sin(2*np.pi*f*t+1.3*np.exp(-t*3)*np.sin(2*np.pi*f*3*t))*np.exp(-t*2.5)*0.22
def swell(dur):   # reversed-cymbal style swell
    n=int(dur*SR); t=np.arange(n)/SR
    return bp(rng.standard_normal(n),1500,5000)*(t/dur)**3*0.35
def shaker(v=1):
    n=int(0.06*SR); t=np.arange(n)/SR
    return bp(rng.standard_normal(n),3000,5500)*np.minimum(t/0.008,1)*np.exp(-t*60)*0.08*v


# v6: + guitar arps, choir, counter-bells, fuller groove, new intro.
# Lo-fi, warbly, mid-heavy dark instrumental. G minor, 120 BPM. Original composition.
import numpy as np, soundfile as sf, sys
from scipy.signal import butter, sosfilt, fftconvolve
SR=44100; BPM=120; BEAT=60/BPM; BAR=4*BEAT; S16=BEAT/4
rng=np.random.default_rng(5)
def m2f(m): return 440*2**((m-69)/12)
def flt(x,kind,fc,o=2): return sosfilt(butter(o,fc,kind,fs=SR,output='sos'),x,axis=0)
def lp(x,fc,o=2): return flt(x,'low',min(fc,SR*0.45),o)
def hp(x,fc,o=2): return flt(x,'high',fc,o)
def bp(x,lo,hi,o=2): return flt(x,'band',[lo,min(hi,SR*0.45)],o)
NBARS=36; N=int((NBARS*BAR+6)*SR); TR={}
def add(trk,t,sig,pan=0.0,g=1.0):
    if trk not in TR: TR[trk]=np.zeros((N,2))
    i=max(int(t*SR),0); sig=sig[:max(N-i,0)]*g
    TR[trk][i:i+len(sig),0]+=sig*np.cos((pan+1)*np.pi/4)*1.414
    TR[trk][i:i+len(sig),1]+=sig*np.sin((pan+1)*np.pi/4)*1.414
def phase(f): return np.cumsum(f)/SR
def pulse(ph,w=0.4): return np.where((ph%1)<w,1.0,-1.0)
def saw(ph): return 2*(ph%1)-1

# ---------- instruments
def organ(ms,dur):
    """reedy, accordion/organ-like chord with slow beating"""
    n=int(dur*SR); t=np.arange(n)/SR; s=np.zeros(n)
    for m in ms:
        for d in (-0.09,0.08):
            f=m2f(m)*2**(d/12)*(1+0.002*np.sin(2*np.pi*(0.4+rng.random())*t))
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
    vib=1+0.011*np.sin(2*np.pi*5.8*t)*np.clip(a,0,1)
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

# ---------- harmony: chord every 2 beats (own progression)
Gm=[55,58,62]; Gm_F=[53,58,62]; Eb=[55,58,63]; Cm=[55,60,63]; Bb=[53,58,62]; Ab=[56,60,63]; D=[54,57,62]; Fm=[56,60,65]
ROOT={id(Gm):43,id(Gm_F):41,id(Eb):39,id(Cm):36,id(Bb):46,id(Ab):44,id(D):38,id(Fm):41}
PROG_A=[Gm,Gm_F,Eb,Cm, Gm,Bb,Ab,D]          # 4 bars
PROG_B=[Cm,Ab,Eb,Bb, Fm,Ab,D,D]             # 4 bars
def sec(b): return 'intro' if b<4 else 'A1' if b<12 else 'B1' if b<20 else 'A2' if b<28 else 'B2' if b<34 else 'outro'
for b in range(NBARS):
    s_=sec(b); t0=b*BAR; prog=PROG_B if s_.startswith('B') else PROG_A
    for h in range(2):
        ch=prog[(b%4)*2+h]; r=ROOT[id(ch)]; th=t0+h*2*BEAT
        if not (s_=='intro' and b<2): add('organ',th,organ(ch+([ch[0]+12] if s_.startswith('B') else []),2*BEAT+0.04),(-0.3,0.3)[h],(0.8+0.5*(b-2+h/2)) if s_=='intro' else 1.0)
        if s_!='intro':
            # bass: pulsing 8ths with a pickup
            for k,(st,l) in enumerate([(0,3),(3,1),(4,2),(6,2)]):
                add('bass',th+st*S16,bassline(r+(12 if k==3 and h==1 else 0),l*S16*0.95))
    # guitar arpeggio (whole track except B2 where choir carries)
    GP=[(0,0),(2,1),(4,2),(6,1),(8,3),(10,1),(12,2),(14,1)]
    for st,ix in GP:
        ch=prog[(b%4)*2+st//8]; notes_=[ch[0],ch[1],ch[2],ch[0]+12]
        trk='igtr' if s_=='intro' else 'gtr'
        add(trk,t0+st*S16+rng.normal(0,0.006),ks(notes_[ix]+(0 if s_=='intro' else 12 if st%4==2 and s_.startswith('B') else 0),0.9,1.6,0.45),(-0.45,0.45)[(st//2)%2],0.9 if st in(0,8) else 0.65)
    # choir in B sections and outro
    if s_.startswith('B') or s_=='outro':
        for h in range(2):
            ch=prog[(b%4)*2+h]; add('choir',t0+h*2*BEAT,choir(ch,2*BEAT+0.4),0)
    # counter-bells in A2
    if s_=='A2':
        for k,st in enumerate((3,6,11,14)):
            ch=prog[(b%4)*2+st//8]; add('bell',t0+st*S16,bell(ch[(k+b)%3]+24),(0.5,-0.5)[k%2])
    # tremolo counter-line (high, quiet, warbly) in B sections
    if s_.startswith('B'):
        for st in range(0,16,2):
            ch=prog[(b%4)*2+st//8]; add('organ',t0+st*S16,organ([ch[(st//2)%3]+12],S16*1.8)*0.6,0.5)
    # pitch drops at section starts and every 4 bars in B
    if b in (4,12,20,28) or (s_.startswith('B') and b%2==1):
        add('fx',t0+(0 if b%2==0 else 3*BEAT),drop(),0.0)
    # drums: buried, soft
    if s_ in('A1','B1','A2','B2'):
        for st in ([0,10] if b%2==0 else [0,6,10]): add('kick',t0+st*S16,kick())
        for st in (4,12): add('snare',t0+st*S16,snare(),0.1)
        for st in range(0,16,2): add('hat',t0+st*S16+(0.012 if st%4 else 0),hat(1 if st%4==2 else 0.6),-0.3)
        for st in range(16): add('hat',t0+st*S16+(0.01 if st%2 else 0),shaker(1 if st%2 else 0.5),0.35)
        for st in ((7,15) if b%2 else (15,)): add('snare',t0+st*S16,snare()*0.25,-0.15)

add('fx',3*BAR,swell(BAR),0.0)
# intro lead teaser (bar 2-3), quiet
TEASE=[(0,62,4,0),(4,63,4,0),(8,62,6,0),(16,67,4,0),(20,66,4,0),(24,62,8,-5)]
# ---------- melodies (original): (step16, midi, len16, dive semitones)
MA=[(0,67,3,0),(3,70,3,0),(6,69,2,0),(8,67,6,0),(14,65,2,0),
    (16,67,3,0),(19,62,3,0),(22,63,2,0),(24,62,8,-5),
    (32,70,3,0),(35,72,3,0),(38,70,2,0),(40,68,6,0),(46,67,2,0),
    (48,66,4,0),(52,67,4,0),(56,62,8,-7)]
MB=[(0,75,4,0),(4,74,2,0),(6,72,2,0),(8,75,6,0),(14,77,2,0),
    (16,74,6,0),(22,72,2,0),(24,70,8,0),
    (32,72,4,0),(36,70,2,0),(38,68,2,0),(40,67,6,0),(46,68,2,0),
    (48,66,8,0),(56,67,8,-12)]
notes=[]
notes+=[(2*BAR+s*S16,m,l*S16,d) for s,m,l,d in TEASE]
for b0,M in ((4,MA),(8,MA),(12,MB),(16,MB),(20,MA),(24,MA),(28,MB),(32,MA[:9])):
    notes+=[(b0*BAR+s*S16+rng.normal(0,0.008),m,l*S16,d) for s,m,l,d in M]
notes.sort(); add('lead',0,lead(notes,N/SR),0.0)

# ---------- mix
def reverb(x,dec,mix):
    n=int(dec*SR); t=np.arange(n)/SR; ir=np.stack([lp(rng.standard_normal(n),4000)*np.exp(-t*6.9/dec) for _ in range(2)],1)
    w=np.stack([fftconvolve(x[:,c],ir[:,c])[:len(x)] for c in range(2)],1); return w*mix/np.sqrt((ir**2).sum()/2)
TR['igtr']=bp(TR['igtr'],450,2600,2)*1.8
tt=np.arange(N)/SR; TR['lead']*=np.where(tt<4*BAR,0.6,1.0)[:,None]
G={'organ':1.0,'bass':0.8,'lead':1.0,'fx':0.7,'kick':0.65,'snare':0.5,'hat':0.6,'gtr':0.7,'igtr':0.9,'choir':0.75,'bell':0.5}
mix=sum(TR[k]*g for k,g in G.items())
mix+=reverb(TR['organ']*0.35+TR['lead']*0.5+TR['snare']*0.4+TR['fx']*0.4+TR['gtr']*0.3+TR['igtr']*0.6+TR['choir']*0.5+TR['bell']*0.6,2.8,0.38)
# tape: band-limit, saturate, wow & flutter, hiss
mix=hp(mix,110,4); mix=lp(mix,5200,4)
mix=mix+bp(mix,300,1500)*0.35
mix/=np.abs(mix).max(); mix=np.tanh(mix*2.2)
t=np.arange(len(mix))/SR
d=(0.004+0.0018*np.sin(2*np.pi*0.55*t)+0.0006*np.sin(2*np.pi*1.3*t+1)+0.00008*np.sin(2*np.pi*7*t))*SR
idx=np.clip(np.arange(len(mix))-d,0,len(mix)-1)
mix=np.stack([np.interp(idx,np.arange(len(mix)),mix[:,c]) for c in range(2)],1)
mix+=lp(hp(rng.standard_normal((len(mix),2)),1500),5000)*0.006
mix=lp(mix,6000,2)
mix*=0.95/np.abs(mix).max()
end=int((NBARS*BAR+3)*SR); mix=mix[:end]; fo=int(4*SR); mix[-fo:]*=np.linspace(1,0,fo)[:,None]**1.3
fi=int(0.03*SR); mix[:fi]*=np.linspace(0,1,fi)[:,None]
sf.write(sys.argv[1],mix.astype(np.float32),SR); print('ok',len(mix)/SR)

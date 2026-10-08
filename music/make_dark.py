# Dark rap instrumental, G minor (phrygian colour), 120 BPM half-time. Original composition.
import numpy as np, soundfile as sf, sys
from scipy.signal import butter, sosfilt, fftconvolve
SR=44100; BPM=120; BEAT=60/BPM; BAR=4*BEAT; S16=BEAT/4
rng=np.random.default_rng(23)
def m2f(m): return 440*2**((m-69)/12)
def flt(x,kind,fc,o=2): return sosfilt(butter(o,fc,kind,fs=SR,output='sos'),x,axis=0)
def lp(x,fc,o=2): return flt(x,'low',min(fc,SR*0.45),o)
def hp(x,fc,o=2): return flt(x,'high',fc,o)
def bp(x,lo,hi,o=2): return flt(x,'band',[lo,min(hi,SR*0.45)],o)
NBARS=40; N=int((NBARS*BAR+6)*SR); TR={}
def add(trk,t,sig,pan=0.0,g=1.0):
    if trk not in TR: TR[trk]=np.zeros((N,2))
    i=int(t*SR); sig=sig[:max(N-i,0)]*g
    TR[trk][i:i+len(sig),0]+=sig*np.cos((pan+1)*np.pi/4)*1.414
    TR[trk][i:i+len(sig),1]+=sig*np.sin((pan+1)*np.pi/4)*1.414
def osc_saw(f,n,det=(-0.1,0,0.1)):
    t=np.arange(n)/SR; return sum(2*((f*2**(d/12)*t+rng.random())%1)-1 for d in det)/len(det)

# --- instruments
def stab(ms,dur):
    n=int(dur*SR); t=np.arange(n)/SR; s=sum(osc_saw(m2f(m),n) for m in ms)/len(ms)
    fe=np.exp(-t*12); s=lp(s,500)*(1-fe)+lp(s,1600)*fe
    e=np.minimum(t/0.004,1)*np.exp(-t*4.5); e*=np.clip((dur-t)/0.03,0,1)
    return bp(s,120,2500)*e*0.6
def strings(ms,dur):
    n=int(dur*SR); t=np.arange(n)/SR; s=np.zeros(n)
    for m in ms:
        vib=1+0.003*np.sin(2*np.pi*(4.8+rng.random())*t+rng.random()*6)
        for d in (-0.07,0.06):
            ph=np.cumsum(m2f(m)*2**(d/12)*vib)/SR; s+=2*((ph+rng.random())%1)-1
    s=bp(s,120,1600)/(len(ms)*2)
    return s*np.minimum(t/0.6,1)*np.clip((dur-t)/0.4,0,1)*0.45
def bell(m,dur=1.6):
    n=int(dur*SR); t=np.arange(n)/SR; f=m2f(m)
    return (np.sin(2*np.pi*f*t+1.6*np.exp(-t*4)*np.sin(2*np.pi*f*2*t))*np.exp(-t*2.6)+0.3*np.sin(2*np.pi*f*4*t)*np.exp(-t*9))*0.3
def lead(notes,T):
    n=int(T*SR); f=np.zeros(n); a=np.zeros(n); t=np.arange(n)/SR; cur=m2f(notes[0][1])
    for s,m,l in notes:
        i0=int(s*SR); i1=min(int((s+l)*SR),n); tgt=m2f(m); seg=np.full(i1-i0,tgt); g=min(int(0.04*SR),len(seg))
        seg[:g]=cur*(tgt/cur)**np.linspace(0,1,g); f[i0:i1]=seg; cur=tgt
        k=np.arange(i1-i0)/SR; a[i0:i1]=np.maximum(a[i0:i1],np.minimum(k/0.02,1)*np.clip((l-k)/0.08,0,1)*(0.8+0.2*np.exp(-k*4)))
    idx=np.where(f>0,np.arange(n),0); np.maximum.accumulate(idx,out=idx); f=f[idx]; f[f==0]=m2f(notes[0][1])
    vib=1+0.005*np.sin(2*np.pi*5.5*t)*a
    ph=np.cumsum(f*vib)/SR
    s=(2*(ph%1)-1)*0.5+(2*((ph*1.004+0.3)%1)-1)*0.5+0.4*np.sin(2*np.pi*ph*0.5)
    return np.tanh(lp(s,1500)*a*1.4)*0.4
def kick():
    n=int(0.4*SR); t=np.arange(n)/SR
    return np.tanh(2*np.sin(2*np.pi*np.cumsum(52+90*np.exp(-t*30))/SR)*np.exp(-t*9)+lp(rng.standard_normal(n),4000)*np.exp(-t*300)*0.3)*0.9
def snare():
    n=int(0.4*SR); t=np.arange(n)/SR
    s=bp(rng.standard_normal(n),1500,9000)*np.exp(-t*13)+np.sin(2*np.pi*200*t)*np.exp(-t*25)*0.5
    c=sum(bp(rng.standard_normal(n),1000,6000)*np.exp(-np.clip(t-d,0,None)*60)*(t>=d) for d in (0,0.01,0.02))*0.4
    return np.tanh(1.4*(s+c))*0.6
def hat(v=1):
    n=int(0.05*SR); t=np.arange(n)/SR; return bp(rng.standard_normal(n),5000,9000)*np.exp(-t*90)*0.18*v
def b808(m,dur,glide=None):
    n=int(dur*SR); t=np.arange(n)/SR; f=np.full(n,m2f(m))
    if glide is not None: g=int(0.08*SR); f[:g]=np.linspace(m2f(glide),m2f(m),g)
    s=np.sin(2*np.pi*np.cumsum(f)/SR)
    e=np.minimum(t/0.003,1)*np.exp(-t*1.1); e*=np.clip((dur-t)/0.04,0,1)
    return np.tanh(2.5*s)*e*0.5

# --- form & harmony (own progressions)
A=[([55,58,62],43),([55,58,63],39),([56,60,63],44),([54,57,62],38)]   # Gm Eb Ab D
B=[([55,60,63],36),([56,60,63],44),([55,58,63],39),([54,57,62],38)]   # Cm Ab Eb D
def sec(b):
    return 'intro' if b<4 else 'v1' if b<12 else 'hook' if b<20 else 'v2' if b<28 else 'hook2' if b<36 else 'outro'
STAB=[0,3,6,10,12,14]      # own syncopated stab pattern
STAB2=[0,3,7,8,11,14]
for b in range(NBARS):
    s_=sec(b); t0=b*BAR
    chord,root=(B if s_ in('hook','hook2') and (b//4)%2==1 else A)[b%4]
    add('str',t0,strings([chord[0]-12]+chord,BAR+0.3),0,1.0 if s_ not in('v1','v2') else 0.7)
    if s_!='intro' or b>=2:
        for k,s in enumerate(STAB if b%2==0 else STAB2):
            add('stab',t0+s*S16,stab([m for m in chord],S16*(2 if k%2 else 1.6)),pan=(-0.25,0.25)[k%2])
    if s_ in('intro','outro') or s_.startswith('hook'):
        for k,m in enumerate([chord[2]+24,chord[0]+24,chord[1]+24,chord[0]+24]):
            add('bell',t0+k*BEAT+(0 if k%2==0 else S16),lp(bell(m-12),1800),0.4-0.25*k,0.55)
    drums = s_ not in('intro','outro') or (s_=='outro' and b<38)
    if drums:
        kp=[0,7,10] if b%2==0 else [0,3,10,13]
        for s in kp: add('kick',t0+s*S16,kick())
        add('snare',t0+8*S16,snare(),0.05)                       # half-time snare on 3
        if b%4==3: add('snare',t0+15*S16,snare()*0.5,-0.1)
        for s in range(0,16,2):
            add('hat',t0+s*S16,hat(1 if s%4==0 else 0.7),0.3)
        if b%2==1:  # trap roll
            for k in range(6): add('hat',t0+12*S16+k*S16*2/3,hat(0.5+0.08*k),0.3)
        for s,l,gl in ([(0,6,None),(7,3,None),(10,6,root+7)] if b%2==0 else [(0,3,None),(3,7,None),(10,3,None),(13,3,root+5)]):
            add('808',t0+s*S16,b808(root-12,l*S16,(gl-12) if gl else None))
# dark layers: low drone, choir 'ooh', vinyl crackle
def choir(ms,dur):
    n=int(dur*SR); t=np.arange(n)/SR; s=np.zeros(n)
    for m in ms:
        for d in (-0.15,0,0.12):
            vib=1+0.004*np.sin(2*np.pi*(5+rng.random())*t+rng.random()*6)
            s+=np.tanh(1.5*np.sin(2*np.pi*np.cumsum(m2f(m)*2**(d/12)*vib)/SR))
    s=bp(s,250,450)*1.0+bp(s,600,900)*0.5     # 'oo' formants
    return s/(len(ms)*3)*np.minimum(t/0.9,1)*np.clip((dur-t)/0.6,0,1)*0.6
for b in range(NBARS):
    if sec(b) in('hook','hook2','outro','intro'):
        chord,root=(B if sec(b) in('hook','hook2') and (b//4)%2==1 else A)[b%4]
        add('choir',b*BAR,choir([c-12 for c in chord],BAR+0.5),0)
t=np.arange(N)/SR
drone=np.sin(2*np.pi*m2f(31)*t)*0.5+lp(rng.standard_normal(N),180)*0.6
drone*=0.6+0.4*np.sin(2*np.pi*t/16)
add('drone',0,np.tanh(drone)*0.35,0)
vin=lp(hp(rng.standard_normal(N),800),5000)*0.02
cr=(rng.random(N)<0.0004)*rng.standard_normal(N)*0.6; vin+=lp(cr,6000)
add('vinyl',0,vin,0)
# lead melody (original), phrases of 4 bars: (step16, midi, len16)
P1=[(0,67,6),(6,68,2),(8,67,4),(12,62,4),(16,63,6),(22,62,2),(24,60,8),
    (32,68,4),(36,67,4),(40,63,6),(46,62,2),(48,62,6),(54,63,2),(56,66,8)]
P2=[(0,70,4),(4,68,2),(6,67,2),(8,68,6),(14,67,2),(16,63,4),(20,67,4),(24,68,8),
    (32,70,4),(36,72,4),(40,70,4),(44,68,4),(48,67,6),(54,66,2),(56,67,8)]
notes=[]
for b0,P in ((12,P1),(16,P2),(28,P1),(32,P2),(36,P1)):
    notes+=[(b0*BAR+s*S16,m,l*S16) for s,m,l in P]
# sparse counter-melody in verses (low, quiet)
for b0 in (4,8,20,24):
    notes+=[(b0*BAR+s*S16,m-12,l*S16) for s,m,l in P1[::4]]
notes.sort(); add('lead',0,lead(notes,N/SR),0)
def riser(d):
    n=int(d*SR); t=np.arange(n)/SR; x=rng.standard_normal(n); o=np.zeros(n)
    for i in range(0,n,2048): fc=400+8000*(i/n)**2; o[i:i+2048]=bp(x[i:i+2048],fc*0.6,fc*1.4)
    return o*(t/d)**2*0.3
for b0 in (10,26): add('fx',b0*BAR,riser(2*BAR))
# --- mix
ke=lp(np.abs(TR['kick'][:,0]),10,1); ke/=ke.max(); duck=1-0.4*np.clip(ke*2.5,0,1)
for k in ('str','stab','808'): TR[k]*=duck[:,None]
def reverb(x,dec,mix):
    n=int(dec*SR); t=np.arange(n)/SR; ir=np.stack([lp(rng.standard_normal(n),5500)*np.exp(-t*6.9/dec) for _ in range(2)],1)
    w=np.stack([fftconvolve(x[:,c],ir[:,c])[:len(x)] for c in range(2)],1); return w*mix/np.sqrt((ir**2).sum()/2)
def delay(x,d,fb,mix):
    D=int(d*SR); y=np.zeros_like(x)
    for i in range(1,7):
        if D*i<len(x): y[D*i:]+=x[:-D*i][:, ::(-1 if i%2 else 1)]*fb**(i-1)
    return lp(hp(y,300),3500)*mix
G={'kick':0.85,'snare':0.7,'hat':0.45,'808':0.75,'str':0.95,'stab':0.8,'bell':0.6,'lead':1.0,'fx':0.45,'drone':0.6,'choir':0.7,'vinyl':0.35}
mix=sum(TR[k]*g for k,g in G.items())
mix+=reverb(TR['lead']*0.55+TR['str']*0.4+TR['stab']*0.35+TR['bell']*0.7+TR['snare']*0.35+TR['choir']*0.5,4.0,0.5)
mix+=delay(TR['lead']*0.45+TR['bell']*0.3,BEAT*0.75,0.38,0.3)
mix=hp(mix,32); mix=lp(mix,7000,2)+bp(mix,300,1500)*0.3   # dark, mid-heavy
mix/=np.abs(mix).max(); mix=np.tanh(mix*2)/np.tanh(2); mix*=0.95/np.abs(mix).max()
end=int((NBARS*BAR+3)*SR); mix=mix[:end]; fo=int(4*SR); mix[-fo:]*=np.linspace(1,0,fo)[:,None]**1.3
sf.write(sys.argv[1],mix.astype(np.float32),SR); print('ok',len(mix)/SR)

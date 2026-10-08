import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve
SR=44100; BPM=120; BEAT=60/BPM; BAR=4*BEAT; S16=BEAT/4
rng=np.random.default_rng(7)
def m2f(m): return 440*2**((m-69)/12)
def lp(x,fc,o=2): return sosfilt(butter(o,min(fc,SR*0.45),'low',fs=SR,output='sos'),x)
def hp(x,fc,o=2): return sosfilt(butter(o,fc,'high',fs=SR,output='sos'),x)
def bp(x,lo,hi): return sosfilt(butter(2,[lo,hi],'band',fs=SR,output='sos'),x)
def env(n,a,d,s,r,sus_len=None):
    a=int(a*SR); d=int(d*SR); r=int(r*SR); e=np.zeros(n)
    if sus_len is None: sus_len=n-r
    sus_len=max(min(sus_len,n),1)
    k=np.arange(n)
    e=np.where(k<a,k/max(a,1),np.where(k<a+d,1-(1-s)*(k-a)/max(d,1),s))
    rel=k>=sus_len; e[rel]=e[sus_len-1]*np.clip(1-(k[rel]-sus_len)/max(r,1),0,1)
    return e
def saw(f,t,ph=0): return 2*((f*t+ph)%1)-1
NBARS=36; N=int(NBARS*BAR*SR)+SR*4
L={k:np.zeros((N,2)) for k in ['kick','snare','hat','bass','pad','arp','lead','fx','bell']}
def add(trk,start,sig,pan=0.0):
    i=int(start*SR); sig=sig[:N-i]
    l=np.cos((pan+1)*np.pi/4); r=np.sin((pan+1)*np.pi/4)
    L[trk][i:i+len(sig),0]+=sig*l*1.414; L[trk][i:i+len(sig),1]+=sig*r*1.414

# ---- instruments
def kick(): 
    n=int(0.45*SR); t=np.arange(n)/SR
    f=48+120*np.exp(-t*28); ph=2*np.pi*np.cumsum(f)/SR
    s=np.sin(ph)*np.exp(-t*11); click=bp(rng.standard_normal(n),2000,6000)*np.exp(-t*300)*0.3
    return np.tanh(2.2*(s+click))*0.9
def snare():
    n=int(0.35*SR); t=np.arange(n)/SR
    nz=bp(rng.standard_normal(n),1200,9000)*np.exp(-t*16)
    tone=np.sin(2*np.pi*190*t)*np.exp(-t*30)*0.6
    clap=sum(bp(rng.standard_normal(n),900,5000)*np.exp(-np.clip(t-d,0,None)*60)*(t>=d) for d in (0,0.011,0.022))*0.5
    return np.tanh(1.5*(nz+tone+clap))*0.7
def hat(open_=False):
    n=int((0.25 if open_ else 0.06)*SR); t=np.arange(n)/SR
    return hp(rng.standard_normal(n),7000,4)*np.exp(-t*(14 if open_ else 70))*0.35
def bass(m,dur):
    n=int(dur*SR); t=np.arange(n)/SR; f=m2f(m)
    s=np.sin(2*np.pi*f*t)+0.35*lp(saw(f,t),900)
    return np.tanh(1.6*s)*env(n,0.004,0.1,0.85,0.05)*0.55
def pad(ms,dur):
    n=int(dur*SR); t=np.arange(n)/SR; s=np.zeros(n)
    for m in ms:
        for dt in (-0.12,-0.04,0.05,0.13): s+=saw(m2f(m)*2**(dt/12),t,rng.random())
    s=lp(s,1800,2)/ (len(ms)*4)
    return s*env(n,0.35,0.5,0.8,0.6,int((dur-0.6)*SR))*0.5
def pluck(m,dur=0.35,bright=4500):
    n=int(dur*SR); t=np.arange(n)/SR; f=m2f(m)
    s=0.5*saw(f,t)+0.5*saw(f*1.004,t,0.3)+0.3*np.sign(np.sin(2*np.pi*f*t))
    # filter env: apply in two bands blended
    e=np.exp(-t*14)
    bright_s=lp(s,bright); dark=lp(s,700)
    return (bright_s*e+dark*(1-e))*env(n,0.002,0.18,0.25,0.08)*0.32
def bell(m,dur=1.2):
    n=int(dur*SR); t=np.arange(n)/SR; f=m2f(m)
    mod=np.sin(2*np.pi*f*3.5*t)*2.0*np.exp(-t*5)
    return np.sin(2*np.pi*f*t+mod)*np.exp(-t*3.2)*0.25
def lead(m,dur,glide_from=None):
    n=int(dur*SR); t=np.arange(n)/SR; f=np.full(n,m2f(m))
    if glide_from is not None:
        g=int(0.06*SR); f[:g]=np.linspace(m2f(glide_from),m2f(m),g)
    vib=1+0.006*np.sin(2*np.pi*5.5*t)*np.clip((t-0.18)/0.3,0,1)
    ph=np.cumsum(f*vib)/SR
    s=sum(2*((ph*2**(d/12)+o)%1)-1 for d,o in ((-0.1,0),(0.1,.37),(0,.71)))/3
    s=lp(s,3800)+0.25*np.sin(2*np.pi*ph)
    return s*env(n,0.012,0.15,0.75,0.12,int((dur-0.1)*SR))*0.33

# ---- harmony: G harmonic minor  Gm | Eb | Cm | D
G3=55
prog=[ ('Gm',[55,58,62],43), ('Eb',[55,58,63],39), ('Cm',[55,60,63],36), ('D',[54,57,62],38) ]
prog2=[ ('Gm',[55,58,62],43), ('Eb',[55,58,63],39), ('Bb',[53,58,62],46), ('D',[54,57,62],38) ]
arp_pat=[0,1,2,1, 2,0,1,2, 0,1,2,3, 2,1,0,1]  # indices into chord+octave
def arp_notes(ch): c=ch+[ch[0]+12]; return [c[i]+12 for i in arp_pat]

# melody (original) in G harmonic minor, 16th grid: (step, midi, len_steps)
melA=[(0,74,6),(6,72,2),(8,70,4),(12,69,4),
      (16,70,6),(22,72,2),(24,74,4),(28,75,4),
      (32,72,6),(38,70,2),(40,67,4),(44,70,4),
      (48,69,8),(56,66,4),(60,69,4)]
melB=[(0,79,4),(4,77,2),(6,75,2),(8,74,6),(14,72,2),
      (16,75,4),(20,74,2),(22,72,2),(24,70,8),
      (32,72,4),(36,74,2),(38,75,2),(40,77,4),(44,75,4),
      (48,74,6),(54,72,2),(56,73,2),(58,74,6)]

# sections (bar ranges)
# 0-3 intro (pad+bells, filtered arp), 4-11 verse (drums light+arp+bass+melA),
# 12-15 build, 16-23 drop (full + melB), 24-27 break (melA bells), 28-35 final drop
def section(b):
    if b<4: return 'intro'
    if b<12: return 'verse'
    if b<16: return 'build'
    if b<24: return 'drop'
    if b<28: return 'break'
    return 'drop2'

for b in range(NBARS):
    sec=section(b); t0=b*BAR
    name,ch,root=(prog if sec in('intro','verse','break') or (b//4)%2==0 else prog2)[b%4]
    # pad
    if sec!='build' or b%4<3: add('pad',t0,pad(ch+[ch[0]-12] if sec.startswith('drop') else ch,BAR),0)
    # arp
    if sec!='intro' or b>=2:
        notes=arp_notes(ch)
        for i,mm in enumerate(notes):
            br={'intro':900+b*500,'verse':2500,'build':1500+(b-12)*900+i*40,'drop':5500,'break':1800,'drop2':6000}[sec]
            add('arp',t0+i*S16,pluck(mm,0.3,br),pan=0.35 if i%2 else -0.35)
    # bells on downbeats in intro/break
    if sec in('intro','break'):
        for k,mm in enumerate([ch[2]+24,ch[1]+24,ch[0]+24,ch[1]+24]):
            add('bell',t0+k*BEAT,bell(mm),pan=0.5-0.33*k)
    # bass
    if sec in('verse','drop','drop2') or (sec=='build'):
        rhythm=[(0,3),(3,3),(6,2),(8,3),(11,3),(14,2)] if sec!='verse' else [(0,6),(6,2),(8,6),(14,2)]
        for st,ln in rhythm:
            if sec=='build' and b%4==3 and st>=8: continue
            add('bass',t0+st*S16,bass(root-12 if st not in(6,14) else root,ln*S16*0.95))
    # drums
    if sec in('verse','drop','drop2'):
        kp=[0,8] if sec=='verse' else [0,7,10]
        for beat in range(4):
            for st in kp if sec!='verse' else [0]:
                if sec=='verse' and beat in(0,2): add('kick',t0+beat*BEAT,kick())
            if sec!='verse': add('kick',t0+beat*BEAT,kick())
            if beat in(1,3): add('snare',t0+beat*BEAT,snare(),0.05)
        if sec!='verse' and b%2==1: add('kick',t0+(3*4+2)*S16,kick()*0.8)
        for s16 in range(16):
            if sec=='verse' and s16%2: continue
            o=(s16%4==2 and sec!='verse')
            v=0.6+0.4*(s16%2==0)
            add('hat',t0+s16*S16,hat(o)*v,pan=0.25)
        if sec in('drop','drop2') and b%4==3:
            for s16 in (13,14,15): add('snare',t0+s16*S16,snare()*0.6,-0.1)
    if sec=='build':
        div={12:4,13:4,14:8,15:16}[b]
        for k in range(div): add('snare',t0+k*BAR/div,snare()*(0.35+0.6*(b-12+k/div)/4))
        if b<15:
            for beat in range(4): add('kick',t0+beat*BEAT,kick()*0.8)
    # melodies
    mel=None
    if sec=='verse': mel=melA; base=4
    if sec in('drop','drop2'): mel=melB; base=16 if sec=='drop' else 28
    if mel is not None and (b-base)%4==0:
        prev=None
        for st,mm,ln in mel:
            add('lead',t0+st*S16,lead(mm,ln*S16+0.1,prev),0.0); prev=mm
            if sec=='drop2': add('lead',t0+st*S16,lead(mm+12,ln*S16+0.1)*0.35,0.0)
    if sec=='break' and (b-24)%4==0:
        for st,mm,ln in melA: add('bell',t0+st*S16,bell(mm+12,1.0)*0.9,-0.2)

# FX: riser in build, impact/downlifter at drops
def riser(dur):
    n=int(dur*SR); t=np.arange(n)/SR; x=rng.standard_normal(n); out=np.zeros(n); seg=SR//20
    for i in range(0,n,seg):
        fc=300+12000*(i/n)**2; out[i:i+seg]=bp(x[i:i+seg+1000],fc*0.7,min(fc*1.3,20000))[:len(out[i:i+seg])]
    return out*(t/dur)**2*0.5
add('fx',12*BAR,riser(4*BAR))
def impact():
    n=int(2.5*SR); t=np.arange(n)/SR
    return (np.sin(2*np.pi*(40+60*np.exp(-t*6))*t)*np.exp(-t*2)+lp(rng.standard_normal(n),3000)*np.exp(-t*3)*0.4)*0.6
for b0 in (4,16,28): add('fx',b0*BAR,impact())
add('fx',26*BAR,riser(2*BAR)*0.8)

# ---- mix: sidechain, reverb, delay
kick_env=np.abs(L['kick'][:,0]); sc=lp(kick_env,12,1); sc=1-0.65*np.clip(sc/ (sc.max()+1e-9)*2.2,0,1)
for k in ('pad','arp','bass','bell'): L[k]*=sc[:,None]
def reverb(x,dec=2.4,mix=0.3):
    n=int(dec*SR); t=np.arange(n)/SR
    ir=np.stack([rng.standard_normal(n)*np.exp(-t*6.9/dec) for _ in range(2)],1)
    ir[:,0]=lp(ir[:,0],6000); ir[:,1]=lp(ir[:,1],6000)
    w=np.stack([fftconvolve(x.mean(1),ir[:,c])[:len(x)] for c in range(2)],1)
    return w/ (np.abs(w).max()+1e-9)*np.abs(x).max()*mix
def delay(x,time,fb=0.35,mix=0.25):
    d=int(time*SR); y=np.zeros_like(x); src=x.copy()
    for i in range(1,6):
        g=fb**i; sh=np.zeros_like(x); sh[d*i:]=src[:-d*i] if d*i<len(src) else 0
        y+= sh[:, ::(-1 if i%2 else 1)]*g
    return lp(y.T,4000).T*mix/ fb
gains={'kick':0.7,'snare':0.85,'hat':0.6,'bass':0.55,'pad':0.8,'arp':0.95,'lead':1.0,'fx':0.45,'bell':0.75}
mix=np.zeros((N,2))
for k,g in gains.items(): mix+=L[k]*g
mix+=reverb(L['pad']*0.5+L['lead']*0.6+L['bell']*0.8+L['snare']*0.3+L['arp']*0.3,2.8,0.45)
mix+=delay(L['lead']*0.6+L['bell']*0.5,BEAT*0.75,0.4,0.3)
mix=hp(mix.T,28).T
# master: gentle glue + limiter
mix/=np.abs(mix).max(); mix=np.tanh(mix*1.8)/np.tanh(1.8)
mix*=0.95/np.abs(mix).max()
# trim / fade
end=int((NBARS*BAR+2.5)*SR); mix=mix[:end]; f=int(2.5*SR); mix[-f:]*=np.linspace(1,0,f)[:,None]**1.5
sf.write('beat.wav',mix.astype(np.float32),SR)
print('ok',len(mix)/SR)

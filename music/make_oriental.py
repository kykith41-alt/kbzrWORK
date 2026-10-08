# Oriental deep-house instrumental, G harmonic minor, 120 BPM. Original composition.
import numpy as np, soundfile as sf, sys
from scipy.signal import butter, sosfilt, fftconvolve
SR=44100; BPM=120; BEAT=60/BPM; BAR=4*BEAT; S16=BEAT/4; SWING=0.12*S16
rng=np.random.default_rng(11)
def m2f(m): return 440*2**((m-69)/12)
def flt(x,kind,fc,o=2):
    return sosfilt(butter(o,fc,kind,fs=SR,output='sos'),x,axis=0)
def lp(x,fc,o=2): return flt(x,'low',min(fc,SR*0.45),o)
def hp(x,fc,o=2): return flt(x,'high',fc,o)
def bp(x,lo,hi,o=2): return flt(x,'band',[lo,min(hi,SR*0.45)],o)
def st(step): return step*S16+(SWING if step%2 else 0)   # swung 16th position

NBARS=40; N=int((NBARS*BAR+6)*SR)
TR={}
def add(trk,t,sig,pan=0.0,g=1.0):
    if trk not in TR: TR[trk]=np.zeros((N,2))
    i=int(t*SR); sig=sig[:max(N-i,0)]*g
    TR[trk][i:i+len(sig),0]+=sig*np.cos((pan+1)*np.pi/4)*1.414
    TR[trk][i:i+len(sig),1]+=sig*np.sin((pan+1)*np.pi/4)*1.414

# ---------- instruments
def ks(m,dur,bright=0.5,decay=None,pick=0.25,t60=1.6):
    """Karplus-Strong nylon string, vectorised per period."""
    f=m2f(m); P=int(round(SR/f)); n=int(dur*SR)
    decay=min(0.9995,np.exp(np.log(0.001)/(f*t60))*(1.0005 if f>300 else 1))
    exc=rng.uniform(-1,1,P); exc=lp(exc,1500+bright*7000)
    # pick position comb
    k=int(P*pick); exc=exc-np.roll(exc,k)*0.6
    y=np.zeros(n+P+1); y[:P]=exc
    for s in range(P,n,P):
        e=min(s+P,n); prev=y[s-P:e-P+1]
        y[s:e]=decay*0.5*(prev[:e-s]+np.concatenate([prev[1:],[0]])[:e-s]) if len(prev)>e-s else decay*0.5*(prev[:e-s]+prev[:e-s])
    out=y[:n]
    body=bp(out,90,4000)+0.3*bp(out,180,260)   # guitar body resonance
    fade=np.ones(n); fade[-800:]=np.linspace(1,0,800)
    return body*fade*0.6
def kick():
    n=int(0.32*SR); t=np.arange(n)/SR
    f=50+95*np.exp(-t*35); s=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*12)
    return np.tanh(1.8*s+lp(rng.standard_normal(n),3000)*np.exp(-t*250)*0.25)*0.95
def clap():
    n=int(0.4*SR); t=np.arange(n)/SR; x=rng.standard_normal(n); s=np.zeros(n)
    for d in (0,0.009,0.019,0.03):
        s+=x*np.exp(-np.clip(t-d,0,None)*(70 if d<0.03 else 18))*(t>=d)
    return bp(s,900,6500)*0.45
def shaker(v=1):
    n=int(0.07*SR); t=np.arange(n)/SR
    return bp(rng.standard_normal(n),4500,9500)*np.minimum(t/0.01,1)*np.exp(-t*55)*0.18*v
def ohat():
    n=int(0.22*SR); t=np.arange(n)/SR
    return bp(rng.standard_normal(n),6000,11000)*np.exp(-t*16)*0.16
def dum():
    n=int(0.35*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*(95+40*np.exp(-t*40))*t)*np.exp(-t*10)*0.55
def tek():
    n=int(0.12*SR); t=np.arange(n)/SR
    return (np.sin(2*np.pi*520*t)*0.5+bp(rng.standard_normal(n),1500,6000))*np.exp(-t*60)*0.32
def bass(m,dur):
    n=int(dur*SR); t=np.arange(n)/SR; f=m2f(m)
    s=np.sin(2*np.pi*f*t)+0.25*np.sin(4*np.pi*f*t)+0.12*np.sin(6*np.pi*f*t)
    e=np.minimum(t/0.005,1)*np.exp(-t*2.2); e[-300:]*=np.linspace(1,0,300)
    return np.tanh(1.3*s)*e*0.6
def pad(ms,dur):
    n=int(dur*SR); t=np.arange(n)/SR; s=np.zeros(n)
    for m in ms:
        for dt in (-0.08,0.0,0.09):
            f=m2f(m)*2**(dt/12)*(1+0.002*np.sin(2*np.pi*0.3*t+rng.random()*6))
            s+=2*((np.cumsum(f)/SR+rng.random())%1)-1
    s=lp(s,1100,2)/(len(ms)*3)
    a=np.minimum(t/0.8,1); r=np.clip((dur-t)/0.5,0,1)
    return s*a*r*0.4
def duduk(notes,t_total):
    """Legato reed lead: notes=(start_s, midi, len_s, grace). One continuous voice."""
    n=int(t_total*SR); f=np.zeros(n); amp=np.zeros(n); t=np.arange(n)/SR
    cur=m2f(notes[0][1])
    for (s,m,l,gr) in notes:
        i0=int(s*SR); i1=min(int((s+l)*SR),n); tgt=m2f(m)
        g=int(0.05*SR)  # glide time
        seg=np.full(i1-i0,tgt)
        gl=min(g,len(seg)); seg[:gl]=cur*(tgt/cur)**(np.linspace(0,1,gl)**0.6)
        if gr:  # grace note: quick flick from upper neighbour
            gi=min(int(0.06*SR),len(seg)); seg[:gi]=m2f(m+gr)
        f[i0:i1]=seg; cur=tgt
        ln=i1-i0; k=np.arange(ln)/SR
        e=np.minimum(k/0.04,1)*(0.85+0.15*np.exp(-k*3))
        e*=np.clip((l-k)/0.06,0,1)
        amp[i0:i1]=np.maximum(amp[i0:i1],e)
    # hold freq through rests so glides start from last note
    last=f[0] if f[0]>0 else m2f(notes[0][1])
    for i in np.flatnonzero(f==0): pass
    nz=f>0; idx=np.where(nz,np.arange(n),0); np.maximum.accumulate(idx,out=idx); f=f[idx]; f[f==0]=m2f(notes[0][1])
    vib_depth=0.007*np.clip(amp,0,1)
    vib=1+vib_depth*np.sin(2*np.pi*5.2*t+0.3*np.sin(2*np.pi*0.7*t))
    ph=np.cumsum(f*vib)/SR
    src=sum((1/k)*np.sin(2*np.pi*k*ph)*(0.9 if k%2 else 0.55) for k in range(1,14))
    breath=bp(rng.standard_normal(n),800,4000)*0.12
    x=(src+breath)*amp
    out=bp(x,350,800)*1.0+bp(x,1050,1600)*0.7+bp(x,2400,3200)*0.25+lp(x,500)*0.4
    return np.tanh(out*1.5)*0.45
def pizz(m,dur=0.5):
    return ks(m,dur,bright=0.9,pick=0.13,t60=0.7)*0.8

# ---------- harmony (G harmonic minor): Gm | Eb | Cm | D
CH=[([55,58,62],43),([55,58,63],39),([55,60,63],36),([54,57,62],38)]
CH_B=[([55,58,62],43),([55,58,63],39),([53,58,62],46),([54,57,62],38)]  # Gm Eb Bb D

def section(b):
    if b<4: return 'intro'
    if b<12: return 'verse'
    if b<16: return 'build'
    if b<28: return 'drop'
    if b<32: return 'break'
    return 'drop2'

# guitar 3-3-2 flamenco-ish pattern: (step, chord-tone index or 'b' bass)
GPAT=[(0,'b'),(3,1),(6,2),(8,'b5'),(10,1),(11,2),(13,1),(14,2)]
for b in range(NBARS):
    sec=section(b); t0=b*BAR
    chord,root=(CH_B if sec in('drop','drop2') and (b//4)%2 else CH)[b%4]
    # pad
    if sec!='drop2' or True:
        add('pad',t0,pad(chord+([chord[0]+12] if sec in('drop','drop2') else []),BAR+0.4),0,0.9 if sec!='build' else 0.6)
    # guitar
    if not (sec=='build' and b==15):
        for s,ix in GPAT:
            if ix=='b': m=root+12
            elif ix=='b5': m=root+19
            else: m=chord[ix]+ (12 if sec in('drop','drop2') and s>8 else 0)
            v=1.0 if s in(0,8) else 0.7
            add('gtr',t0+st(s),ks(m,1.2 if s in(0,8) else 0.6,bright=0.45,t60=2.0),pan=-0.3+0.06*(s%5),g=v)
        if sec in('drop','drop2'):  # rasgueado-ish strums on 2-and & 4
            for s in (6,12):
                for k,m in enumerate(chord+[chord[0]+12]):
                    add('gtr',t0+st(s)+k*0.012,ks(m+12,0.35,bright=0.6,t60=0.6)*0.45,pan=0.35)
    # drums
    groove = sec in('verse','drop','drop2') or (sec=='build' and b<15)
    if groove:
        for beat in range(4): add('kick',t0+beat*BEAT,kick(),0,0.85 if sec=='verse' else 1)
        for s16 in range(16):
            add('shk',t0+st(s16),shaker(1 if s16%2 else 0.6),0.3)
        if sec!='verse' or b>=8:
            for beat in (1,3): add('clap',t0+beat*BEAT,clap(),0.05)
        if sec in('drop','drop2'):
            for beat in range(4): add('hat',t0+beat*BEAT+BEAT/2,ohat(),-0.25)
    # darbuka (maqsum-ish): D T . T D . T .  in 8ths
    if sec in('verse','drop','drop2','break'):
        for i,h in enumerate('DT.TD.T.'):
            if h=='D': add('perc',t0+i*BEAT/2,dum(),-0.4,0.9)
            if h=='T': add('perc',t0+i*BEAT/2+(SWING if i%2 else 0),tek(),0.45)
        if b%2: add('perc',t0+st(15),tek()*0.6,0.5)
    if sec=='build':
        div=[4,4,8,16][b-12]
        for k in range(div): add('clap',t0+k*BAR/div,clap(),0,0.3+0.7*((b-12)*div+k)/(4*div))
    # bass (deep house, off-beat + pickups)
    if sec in('verse','drop','drop2') or (sec=='build' and b<15):
        pat=[(0,root-12,1.5),(2,root,1.5),(6,root,1.5),(10,root,1.0),(11,root+12,0.8),(14,root,1.5)]
        if sec=='verse': pat=[(0,root-12,3),(6,root,1.5),(10,root,1.5),(14,root,1.5)]
        for s,m,l in pat: add('bass',t0+st(s),bass(m-12,l*S16*1.6))

# ---------- melodies (original)
# (step16 from phrase start, midi, len in 16ths, grace semitones or 0)
A=[(0,67,4,0),(4,70,2,2),(6,69,2,0),(8,67,6,0),
   (16,66,2,0),(18,67,2,0),(20,69,4,1),(24,62,6,0),
   (32,72,4,2),(36,70,2,0),(38,69,2,0),(40,70,6,0),
   (48,69,2,0),(50,67,2,0),(52,66,4,0),(56,67,7,0)]
B=[(0,74,3,1),(3,75,1,0),(4,74,2,0),(6,72,2,0),(8,70,4,2),(12,69,2,0),(14,70,2,0),
   (16,72,3,0),(19,70,1,0),(20,69,4,0),(24,67,6,1),(30,66,2,0),
   (32,67,2,0),(34,69,2,0),(36,70,2,0),(38,72,2,0),(40,74,4,1),(44,75,2,0),(46,78,2,0),
   (48,79,6,0),(54,78,1,0),(55,75,1,0),(56,74,7,0)]
def place(mel,bar0,transp=0):
    return [(bar0*BAR+st(s), m+transp, l*S16, g) for s,m,l,g in mel]
lead=[]
lead+= [(1*BAR+st(s),m,l*S16,g) for s,m,l,g in A[:8]]          # intro teaser
for b0 in (4,8): lead+=place(A,b0)
for b0 in (16,20,24): lead+=place(B,b0)
for b0 in (28,): lead+=place(A,b0)
for b0 in (32,36): lead+=place(B,b0)
lead.sort()
dd=duduk(lead,N/SR)
add('lead',0,dd,0.0)
# octave-down pizz doubles in drops
for b0 in (20,24,36):
    for s,m,l,g in B: add('pizz',b0*BAR+st(s),pizz(m-12,0.4),0.45,0.55)
# riser / impacts
def riser(dur):
    n=int(dur*SR); t=np.arange(n)/SR; x=rng.standard_normal(n); out=np.zeros(n); seg=2048
    for i in range(0,n,seg):
        fc=400+9000*(i/n)**2; out[i:i+seg]=bp(x[i:i+seg],fc*0.6,fc*1.4)
    return out*(t/dur)**2*0.35
add('fx',12*BAR,riser(4*BAR),0)
def boom():
    n=int(3*SR); t=np.arange(n)/SR
    return np.sin(2*np.pi*(38+50*np.exp(-t*5))*t)*np.exp(-t*1.8)*0.5+lp(rng.standard_normal(n),2500)*np.exp(-t*2.5)*0.15
for b0 in (16,32): add('fx',b0*BAR,boom())

# ---------- mix
k=np.abs(TR['kick'][:,0]); envk=lp(k,10,1); envk/=envk.max()+1e-9
duck=1-0.55*np.clip(envk*2.5,0,1)
for nm in ('pad','bass','gtr','pizz'): TR[nm]*=duck[:,None]
def reverb(x,dec,mix,pre=0.02,tone=5000):
    n=int(dec*SR); t=np.arange(n)/SR
    ir=np.zeros((n+int(pre*SR),2))
    for c in range(2): ir[int(pre*SR):,c]=lp(rng.standard_normal(n),tone)*np.exp(-t*6.9/dec)
    w=np.stack([fftconvolve(x[:,c],ir[:,c])[:len(x)] for c in range(2)],1)
    return w*mix/np.sqrt((ir**2).sum()/2)
def delay(x,d,fb,mix):
    D=int(d*SR); y=np.zeros_like(x)
    for i in range(1,7):
        if D*i>=len(x): break
        y[D*i:]+=x[:-D*i][:, ::(-1 if i%2 else 1)]*fb**(i-1)
    return lp(hp(y,300),3500)*mix
G={'kick':0.85,'clap':0.6,'shk':0.7,'hat':0.6,'perc':0.6,'bass':0.65,'pad':0.55,'gtr':0.9,'lead':0.95,'pizz':0.5,'fx':0.5}
mix=sum(TR[n]*g for n,g in G.items())
send=TR['lead']*0.5+TR['clap']*0.35+TR['gtr']*0.18+TR['pad']*0.3+TR['pizz']*0.3+TR['perc']*0.15
mix+=reverb(send,3.0,0.35)
mix+=delay(TR['lead']*0.5+TR['pizz']*0.3,BEAT*0.75,0.38,0.35)
mix=hp(mix,30)
# gentle tilt toward mids like the reference: small presence lift
mix+=bp(mix,700,2500)*0.15
mix/=np.abs(mix).max(); mix=np.tanh(mix*2.0)/np.tanh(2.0); mix*=0.95/np.abs(mix).max()
end=int((NBARS*BAR+3)*SR); mix=mix[:end]
fo=int(4*SR); mix[-fo:]*=np.linspace(1,0,fo)[:,None]**1.3
fi=int(0.05*SR); mix[:fi]*=np.linspace(0,1,fi)[:,None]
sf.write(sys.argv[1] if len(sys.argv)>1 else 'beat2.wav',mix.astype(np.float32),SR)
print('ok',len(mix)/SR)

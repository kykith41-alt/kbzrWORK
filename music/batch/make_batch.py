# Batch of 5 original lo-fi dark instrumentals in the style of the user's examples.
# Each track: own key, tempo, progression, generated melody, layer set and arrangement.
import numpy as np, soundfile as sf, sys
import lofi_lib as L
from lofi_lib import SR, lp, hp, bp, m2f
from scipy.signal import fftconvolve

HMIN=[0,2,3,5,7,8,11]      # harmonic minor
NMIN=[0,2,3,5,7,8,10]      # natural minor
# chord = (scale-degree index 0..6, scale) ; triads built by stacking thirds in the scale
PROGS={
 'i-VI-III-VII':[0,5,2,6], 'i-iv-VI-V':[0,3,5,4], 'i-VII-VI-V':[0,6,5,4],
 'i-VI-iv-V':[0,5,3,4],   'iv-VI-i-V':[3,5,0,4],  'i-III-VII-iv':[0,2,6,3],
 'i-v-VI-iv':[0,4,5,3],   'VI-VII-i-i':[5,6,0,0],
}
def triad(tonic,deg,dom=False):
    sc=HMIN if (deg==4 or dom) else NMIN
    notes=[tonic+sc[(deg+k)%7]+12*((deg+k)//7) for k in (0,2,4)]
    # voice into 53..67 range
    out=[]
    for n in notes:
        while n<53: n+=12
        while n>67: n-=12
        out.append(n)
    return sorted(out)

def gen_melody(rng,tonic,chords,bars=4,hi=False,density=0.5):
    """original 4-bar phrase: chord tones on strong steps, stepwise passing tones, dive at end"""
    sc=[tonic+12+o for o in HMIN]+[tonic+24+o for o in HMIN]+[tonic+o for o in HMIN]
    sc=sorted(set(sc)); 
    if hi: sc=[n+12 for n in sc]
    RH=[[4,2,2,6,2],[3,3,2,6,2],[2,2,4,8],[6,2,4,4],[3,3,4,2,4],[4,4,8],[2,2,2,2,8]]
    if density>0.6: RH+= [[2,2,2,2,4,4],[1,1,2,4,2,2,4]]
    if density<0.4: RH=[[8,8],[6,2,8],[4,4,8],[12,4]]
    out=[]; cur=None
    motif=None
    for bar in range(bars):
        rh=RH[rng.integers(len(RH))] if not (bar==2 and motif) else motif[0]
        if bar==0: motif=(rh,)
        st=bar*16
        ch=chords[min(bar*len(chords)//bars, len(chords)-1)]
        for k,ln in enumerate(rh):
            strong=(st%8==0)
            if cur is None or strong:
                cands=[n for n in sc if (n-ch[0])%12 in [(c-ch[0])%12 for c in ch]]
                if cur is not None: cands=sorted(cands,key=lambda n:abs(n-cur))[:3]
                else: cands=[n for n in cands if 64<=n<=74] or cands
                n=cands[rng.integers(len(cands))]
            else:
                i=sc.index(cur) if cur in sc else int(np.argmin([abs(x-cur) for x in sc]))
                i=int(np.clip(i+rng.choice([-2,-1,-1,1,1,2]),0,len(sc)-1)); n=sc[i]
            dive=0
            if bar==bars-1 and k==len(rh)-1: dive=-int(rng.choice([5,7,12]))
            out.append((st,n,ln,dive)); cur=n; st+=ln
    return out

def render(P,path):
    rng=np.random.default_rng(P['seed']); L.rng=rng
    BPM=P['bpm']; BEAT=60/BPM; BAR=4*BEAT; S16=BEAT/4
    form=P['form']                                  # list of (name, bars)
    secs=[]; [secs.extend([nm]*nb) for nm,nb in form]; NB=len(secs)
    N=int((NB*BAR+8)*SR); TR={}
    def add(trk,t,sig,pan=0.0,g=1.0):
        if trk not in TR: TR[trk]=np.zeros((N,2))
        i=max(int(t*SR),0); sig=sig[:max(N-i,0)]*g
        TR[trk][i:i+len(sig),0]+=sig*np.cos((pan+1)*np.pi/4)*1.414
        TR[trk][i:i+len(sig),1]+=sig*np.sin((pan+1)*np.pi/4)*1.414
    T=P['tonic']
    progA=[triad(T,d) for d in PROGS[P['progA']]]
    progB=[triad(T,d) for d in PROGS[P['progB']]]
    hr=P['harm_rhythm']        # chords per bar: 1 or 2
    def chord_at(sec,b,half):
        prog=progB if sec.startswith('B') else progA
        return prog[((b%2)*2+half)%4] if hr==2 else prog[b%4]
    lay=P['layers']
    for b,s_ in enumerate(secs):
        t0=b*BAR; first=(b==0 or secs[b-1]!=s_)
        for h in range(hr):
            ch=chord_at(s_,b,h); dur=BAR/hr; th=t0+h*dur
            root=ch[0]-12
            if 'organ' in lay and not (s_=='intro' and b<P.get('organ_in',2)):
                add('organ',th,L.organ(ch+([ch[0]+12] if s_.startswith('B') else []),dur+0.04),(-0.25,0.25)[h%2],
                    (0.8+0.4*b) if s_=='intro' else 1.0)
            if s_ not in('intro','outro','break'):
                pat=P['bass_pat']
                for st,ln,oc in pat:
                    if st*S16<dur: add('bass',th+st*S16,L.bassline(root-12+oc,ln*S16*0.95))
        if 'gtr' in lay and s_!='outro':
            for st,ix in P['gtr_pat']:
                ch=chord_at(s_,b,st*hr//16); nn=[ch[0],ch[1],ch[2],ch[0]+12]
                trk='igtr' if s_=='intro' else 'gtr'
                add(trk,t0+st*S16+rng.normal(0,0.006),L.ks(nn[ix]+P.get('gtr_oct',0),0.9,1.6,0.45),(-0.4,0.4)[(st//2)%2],0.9 if st%8==0 else 0.65)
        if 'choir' in lay and (s_.startswith('B') or s_=='outro' or (s_=='break')):
            for h in range(hr):
                ch=chord_at(s_,b,h); add('choir',t0+h*BAR/hr,L.choir(ch,BAR/hr+0.4),0)
        if 'bells' in lay and s_ in P.get('bell_secs',('A2',)):
            for k,st in enumerate((3,6,11,14)):
                ch=chord_at(s_,b,st*hr//16); add('bell',t0+st*S16,L.bell(ch[(k+b)%3]+24),(0.4,-0.4)[k%2])
        if 'trem' in lay and s_.startswith('B'):
            for st in range(0,16,2):
                ch=chord_at(s_,b,st*hr//16); add('organ',t0+st*S16,L.organ([ch[(st//2)%3]+12],S16*1.8)*0.55,0.3)
        if 'drops' in lay and ((first and s_ not in('intro',)) or (s_.startswith('B') and b%2==1)):
            add('fx',t0+(0 if first else 3*BEAT),L.drop(),0.0)
        if s_ in P['drum_secs']:
            for st in P['kick_pat'][b%2]: add('kick',t0+st*S16,L.kick())
            for st in P['snare_pat']: add('snare',t0+st*S16,L.snare(),0.1)
            for st in range(0,16,2): add('hat',t0+st*S16+(0.012 if st%4 else 0),L.hat(1 if st%4==2 else 0.6),-0.2)
            if P.get('shaker'):
                for st in range(16): add('hat',t0+st*S16+(0.01 if st%2 else 0),L.shaker(0.5 if st%2 else 0.25),0.2)
            for st in ((7,15) if b%2 else (15,)): add('snare',t0+st*S16,L.snare()*0.22,-0.15)
        if s_=='intro' and b==len([x for x in secs if x=='intro'])-1: add('fx',t0,L.swell(BAR),0)
    # melodies
    mel=[]; phrases={}
    for s_name in set(secs):
        if s_name in('intro','outro','break'): continue
        prog=progB if s_name.startswith('B') else progA
        key=s_name[0]
        if key not in phrases:
            phrases[key]=gen_melody(rng,T,prog,4,hi=(key=='B' and P.get('b_high',True)),density=P['density'])
    b=0
    while b<NB:
        s_=secs[b]
        if s_[0] in phrases and s_ not in('intro','outro','break'):
            ph=phrases[s_[0]]
            # every second repeat: vary last bar
            mel+=[(b*BAR+st*S16+rng.normal(0,0.008),n,ln*S16,d) for st,n,ln,d in ph if st<min(64,(NB-b)*16)]
            b+=4
        else:
            if b==0 and P.get('tease',True):
                ph=phrases.get('A')
                if ph: mel+=[((2*16+st)*S16,n-12,ln*S16,d) for st,n,ln,d in ph[:5] if st<32]
            b+=1
    mel.sort(); add('lead',0,L.lead(mel,N/SR),0.0)
    # ---- mix
    tt=np.arange(N)/SR; barn=np.minimum((tt//BAR).astype(int),NB-1)
    for k in ('igtr',):
        if k in TR: TR[k]=bp(TR[k],450,2600,2)*1.8
    secarr=np.array(secs)[barn]
    isB=np.char.startswith(secarr.astype(str),'B'); active=np.isin(secarr,P['drum_secs'])
    depth=np.where(active,np.where(isB,P['pump'][1],P['pump'][0]),0.0)
    pump=1-depth*np.exp(-((tt%BEAT))/0.11)
    for k in ('organ','gtr','choir','bass','bell'):
        if k in TR: TR[k]*=pump[:,None]
    G={'organ':1.0,'bass':0.8,'lead':P.get('lead_gain',1.0),'fx':0.7,'kick':P.get('drum_gain',0.65),'snare':0.5*P.get('drum_gain',0.65)/0.65,'hat':0.55,'gtr':0.7,'igtr':0.9,'choir':0.75,'bell':0.5}
    mix=sum(TR[k]*g for k,g in G.items() if k in TR)
    gate=np.ones(N)
    def cut(a_,b_):
        a=int(a_*SR); e=int(b_*SR); r=int(0.004*SR)
        gate[a:e]=0; gate[a-r:a]=np.minimum(gate[a-r:a],np.linspace(1,0,r)); gate[e:e+r]=np.minimum(gate[e:e+r],np.linspace(0,1,r))
    for b in range(NB-1):
        nxt=secs[b+1]
        if secs[b].startswith('B') and b%2==1 and nxt==secs[b] and P.get('stops',True): cut(b*BAR+14*S16,(b+1)*BAR)
        if nxt!=secs[b] and nxt not in('outro',) and secs[b]!='intro' and P.get('stops',True): cut(b*BAR+3*BEAT,(b+1)*BAR)
    def reverb(x,dec,m):
        n=int(dec*SR); t=np.arange(n)/SR; ir=np.stack([lp(rng.standard_normal(n),4000)*np.exp(-t*6.9/dec) for _ in range(2)],1)
        w=np.stack([fftconvolve(x[:,c],ir[:,c])[:len(x)] for c in range(2)],1); return w*m/np.sqrt((ir**2).sum()/2)
    send=sum(TR[k]*g for k,g in (('organ',0.35),('lead',0.5),('snare',0.4),('fx',0.4),('gtr',0.3),('igtr',0.6),('choir',0.5),('bell',0.6)) if k in TR)
    mix=mix*gate[:,None]+reverb(send,P.get('verb',2.8),0.38)
    if P.get('tape_stop_bar') is not None:
        a=int((P['tape_stop_bar']*BAR+3*BEAT)*SR); n=int(BEAT*SR); pos=a+np.cumsum(np.linspace(1,0,n)**1.5)
        mix[a:a+n]=np.stack([np.interp(pos,np.arange(N),mix[:,c]) for c in range(2)],1)*np.linspace(1,0.2,n)[:,None]
    M_=(mix[:,0]+mix[:,1])/2; S_=(mix[:,0]-mix[:,1])/2*0.35; mix=np.stack([M_+S_,M_-S_],1)
    mix=hp(mix,110,4); mix=lp(mix,P.get('lp',5200),4); mix=mix+bp(mix,300,1500)*0.35
    mix/=np.abs(mix).max(); mix=np.tanh(mix*2.2)
    d=(0.004+0.0018*np.sin(2*np.pi*P.get('wow',0.55)*tt)+0.0006*np.sin(2*np.pi*1.3*tt+1)+0.00008*np.sin(2*np.pi*7*tt))*SR
    idx=np.clip(np.arange(N)-d,0,N-1)
    mix=np.stack([np.interp(idx,np.arange(N),mix[:,c]) for c in range(2)],1)
    mix+=lp(hp(rng.standard_normal((N,2)),1500),5000)*0.006; mix=lp(mix,6000,2)
    mix*=0.95/np.abs(mix).max()
    end=int((NB*BAR+4)*SR); mix=mix[:end]; fo=int(P.get('fade',8)*SR); mix[-fo:]*=np.linspace(1,0,fo)[:,None]**1.3
    fi=int(0.03*SR); mix[:fi]*=np.linspace(0,1,fi)[:,None]
    sf.write(path,mix.astype(np.float32),SR); print(path,'ok',round(len(mix)/SR,1),'s')

STD_FORM=[('intro',4),('A1',8),('B1',8),('A2',8),('B2',8),('outro',2)]
TRACKS={
 '1_pepel': dict(seed=101,bpm=118,tonic=57,progA='i-VI-III-VII',progB='iv-VI-i-V',harm_rhythm=2,density=0.5,
    layers={'organ','gtr','choir','drops','trem'},form=STD_FORM,drum_secs=('A1','B1','A2','B2'),
    bass_pat=[(0,3,0),(3,1,0),(4,2,0),(6,2,12)],gtr_pat=[(0,0),(2,1),(4,2),(6,1),(8,3),(10,1),(12,2),(14,1)],
    kick_pat=([0,10],[0,6,10]),snare_pat=(4,12),pump=(0.4,0.6),shaker=True,tape_stop_bar=11),
 '2_holod': dict(seed=202,bpm=122,tonic=53,progA='i-iv-VI-V',progB='VI-VII-i-i',harm_rhythm=1,density=0.35,
    layers={'organ','choir','bells','drops'},bell_secs=('A1','A2'),form=[('intro',4),('A1',8),('B1',8),('break',4),('B2',8),('outro',2)],
    drum_secs=('A1','B1','B2'),bass_pat=[(0,6,0),(6,2,0),(8,6,0),(14,2,12)],gtr_pat=[],
    kick_pat=([0,8],[0,8,11]),snare_pat=(4,12),pump=(0.5,0.65),shaker=False,verb=3.6,wow=0.45),
 '3_okraina': dict(seed=303,bpm=120,tonic=50,progA='i-VII-VI-V',progB='i-VI-iv-V',harm_rhythm=2,density=0.7,
    layers={'organ','gtr','trem','drops','bells'},bell_secs=('B2',),form=STD_FORM,drum_secs=('A1','B1','A2','B2'),
    bass_pat=[(0,2,0),(2,2,0),(4,2,12),(6,2,0)],gtr_pat=[(0,0),(3,1),(6,2),(8,3),(11,1),(14,2)],gtr_oct=12,
    kick_pat=([0,7,10],[0,3,10]),snare_pat=(4,12),pump=(0.45,0.6),shaker=True,tape_stop_bar=27,lead_gain=1.1),
 '4_tuman': dict(seed=404,bpm=116,tonic=52,progA='i-III-VII-iv',progB='i-v-VI-iv',harm_rhythm=1,density=0.3,
    layers={'organ','gtr','choir','drops'},form=[('intro',4),('A1',8),('B1',8),('A2',8),('B2',8),('outro',4)],
    drum_secs=('B1','A2','B2'),bass_pat=[(0,8,0),(10,6,0)],gtr_pat=[(0,0),(4,1),(8,2),(12,3)],
    kick_pat=([0],[0,10]),snare_pat=(8,),pump=(0.3,0.5),shaker=False,verb=4.2,lp=4500,wow=0.4,fade=12,b_high=False,drum_gain=0.55),
 '5_noch': dict(seed=505,bpm=124,tonic=48,progA='i-VI-iv-V',progB='i-VII-VI-V',harm_rhythm=2,density=0.65,
    layers={'organ','gtr','choir','trem','drops','bells'},bell_secs=('A2',),form=STD_FORM,drum_secs=('A1','B1','A2','B2'),
    bass_pat=[(0,3,0),(3,3,0),(6,2,12)],gtr_pat=[(0,0),(2,2),(4,1),(6,2),(8,3),(10,2),(12,1),(14,2)],
    kick_pat=([0,6,10],[0,6,10,13]),snare_pat=(4,12),pump=(0.5,0.7),shaker=True,tape_stop_bar=19,drum_gain=0.75),
}
if __name__=='__main__':
    for name in (sys.argv[1:] or TRACKS):
        render(TRACKS[name],f'batch_{name}.wav')

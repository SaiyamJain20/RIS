from math import comb
def binom_ge(n,p,k): return sum(comb(n,i)*p**i*(1-p)**(n-i) for i in range(k,n+1))
def hyp_ge(N,K,n,k): return sum(comb(K,i)*comb(N-K,n-i) for i in range(k,min(n,K)+1))/comb(N,n)
def q_janus(n): return round(n/2) if n>=2 else 0   # JS Math.round: .5 rounds up; python round is banker's -> fix
def q_js(n): import math; return math.floor(n/2+0.5) if n>=2 else 0
def q_strict(n): return n//2+1
doms={'hosp':20,'manu':3,'ins':3,'lab':2}
N=sum(doms.values())
for p in (0.05,0.1,0.2):
  for name,q in (('JANUS round(n/2)',q_js),('strict majority',q_strict)):
    ok=1.0
    for d,n in doms.items(): ok*= (1-binom_ge(n,p,q(n)))
    print(f"p={p} rule={name}: P[some domain captured]={1-ok:.4f}")
  # random committees of same sizes, fixed number of corrupt K = round(p*N)
  K=round(p*N)
  # approximate: P[any committee captured] via union bound over committees of sizes 20,3,3,2 drawn at random (strict majority)
  ub=sum(hyp_ge(N,K,n,q_strict(n)) for n in doms.values())
  print(f"   random assignment (K={K} of N={N}), strict majority, union bound={ub:.4f}")
# minimum coalition for PBC governance capture via sham admission
for name,q in (('JANUS',q_js),('strict',q_strict)):
  m=min(q(n) for n in doms.values())
  print(name,'min corrupt orgs to capture smallest domain =',m,'; sham members needed to reach PBC quorum: s >= N-2a roughly =',N-2*m)
print('--- targeted adversary with a corrupt orgs; random assignment into committees of sizes 20,3,3,2 (strict majority) ---')
for a in (1,2,3,4,6):
  ub=sum(hyp_ge(N,a,n,q_strict(n)) for n in doms.values())
  print(f"a={a}: type-partitioned capture = {'CERTAIN' if a>=2 else 'no'}; random-assignment P[capture] <= {ub:.4f}")

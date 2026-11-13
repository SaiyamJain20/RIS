"""Parse two `forge test --gas-report` outputs (E baseline vs F ledger) and tabulate per-function gas.
Synthetic, local Forge test runs only; gas from Forge's EVM, not a live chain. Usage:
python3 -I gas_compare.py <E-report.txt> <F-report.txt>   -> markdown on stdout."""
import re, sys

def parse(path):
    out, deploy, contract = {}, {}, None
    lines = open(path).read().splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"\|\s*(src/[\w/]+\.sol:\w+) Contract", ln)
        if m:
            contract = m.group(1).split(":")[1]; continue
        if contract and re.match(r"\|\s*\d+\s*\|\s*\d+\s*\|\s*\|", ln):
            c = [x.strip() for x in ln.strip("|").split("|")]
            deploy[contract] = (int(c[0]), int(c[1]))
        if contract:
            c = [x.strip() for x in ln.strip("|").split("|")]
            if len(c) == 6 and c[0] not in ("Function Name",) and all(x.isdigit() for x in c[1:]):
                out[(contract, c[0])] = tuple(int(x) for x in c[1:])
    return out, deploy

e, ed = parse(sys.argv[1]); f, fd = parse(sys.argv[2])
print("| contract.function | E median | F median | delta | E max | F max | E calls | F calls |\n|---|---|---|---|---|---|---|---|")
for k in sorted(set(e) & set(f)):
    ev, fv = e[k], f[k]
    if ev[2] != fv[2] or ev[3] != fv[3]:
        print("| %s.%s | %d | %d | %+d | %d | %d | %d | %d |" % (k[0], k[1], ev[2], fv[2], fv[2]-ev[2], ev[3], fv[3], ev[4], fv[4]))
print("\nF-only functions (median gas, max, calls):")
for k in sorted(set(f) - set(e)):
    v = f[k]; print("- %s.%s: median %d, max %d, calls %d" % (k[0], k[1], v[2], v[3], v[4]))
print("\n(Deployment sizes intentionally omitted: use `forge build --sizes`; this parser mis-read them.)")

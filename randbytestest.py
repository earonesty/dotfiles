import os
import sys
import json
import math
from runstats import Statistics, Regression

__all__ = ["randtest", "randtestall", "buildstats"]

def primes(givenNumber):
    # Initialize a list
    primes = []
    for possiblePrime in range(2, givenNumber + 1):
        # Assume number is prime until shown it is not.
        isPrime = True
        for num in range(2, int(possiblePrime ** 0.5) + 1):
            if possiblePrime % num == 0:
                isPrime = False
                break
        if isPrime:
            primes.append(possiblePrime)
    return(primes)

_primes = [2]

def nearest_prime_gte(v):
    global _primes
    max_gap = v + 1 + int(math.sqrt(v) * math.log(v))
    if _primes[len(_primes)-1] < v:
        _primes = primes(max_gap)
    i = len(_primes) - 1
    while _primes[i] > v:
        i -= 1
    return(_primes[i+1])

class Pattern:
    def __init__(self, data):
        self.l = len(data)
        p = nearest_prime_gte(len(data))
        pad = p-len(data)
        data += data[0:pad]
        self.data = data

    def __iter__(self):
        for i in range(self.l):
            yield self.data[self.i % len(self.data)]
            self.next()

    def next(self):
        raise Exception("Unimplemented")

class Linear(Pattern):
    def __init__(self, data, n):
        super().__init__(data)
        self.i = 0
        self.n = n
        self.name = "l" + str(n)

    def next(self):
        self.i += self.n

# compute summry stats for byte sequences
def getstats(data):
    s = Statistics()
    for e in data:
        s.push(e)
    return statdict(s)

_measures = ["stddev", "mean", "minimum", "maximum", "skewness", "kurtosis"]
def statdict(s):
    d = {}
    for v in _measures:
        try:
            d[v] = getattr(s, v)()
        except ZeroDivisionError:
            if v == "skewness":
                d[v] = 0

    d["count"] = len(s)
    return d

# if you know something about the bytes that show up when programming errors occur, encode them as a known bad pattern here
patterns = [
    lambda d: Linear(d, 1),     # adjacent bytes are related
    lambda d: Linear(d, 2),     # every other byte is related
    lambda d: Linear(d, 3),     # every third byte is related
]

def getregr(block):
    if (len(block) < 4):
        raise Exception("Too little data")

    d = {}
    for pattern in patterns:
        p = pattern(block)

        r = Regression()

        # compute regression for byte sequences
        y=None
        for x in p:
            if y is not None:
                r.push(x, y)
            y=x

        try:
            slope = r.slope()
            intercept = r.intercept()
        except ZeroDivisionError:
            # all xvals are the same, slope is infinite
            # but for our purposes, this is the same as "all y same"
            slope = 0
            intercept = 0

        v = {
                "slope" : slope,
                "intercept" : intercept,
            }
        d[p.name] = v
    return d

def randstats(data):
    # summary stats
    d = getstats(data)

    # various regressions, flattened
    r = getregr(data)

    for n in r.keys():
        for s in r[n].keys():
            v = n + "-" + s
            d[v] = r[n][s]

    if len(data) >= 256:
        # break data into chunks and accumulate stats on each chunk
        s = 0
        for i in range(0, len(data), 128):
            chunk = data[i:i+128]
            v = int.from_bytes(chunk, "big")
            d["chunk" + str(i)] = v
    else:
        # treat data as a single integer
        d["bignum"] = int.from_bytes(data, "big")

    return d

def buildstats(length, count, source, file=None):
    summary = {}

    for i in range(count):
        block = source(length)
        d = randstats(block)
        for v in d.keys():
            if v not in summary:
                summary[v] = Statistics()
            summary[v].push(d[v])
     
    data = {}
    for v in summary.keys():
        s = summary[v]
        data[v] = {
            "count" : len(s),
            "mean" : s.mean(),
            "stddev" : s.stddev()
        }

    data["length"] = length

    if file is not None:
        with open(file, "w") as f:
            json.dump(data, f)

    return data

def z_to_pct(z_score):
    return 0.5 * (1+math.erf(z_score / 2 ** .5))

def zptiles(summary, point, n=1):
    tests = [k for k in point.keys() if k != 'count']
    r = {}
    for k in tests:
        val = point[k]
        stats = summary[k]
        if k != "count":
            zscore = (val - stats["mean"])/(stats["stddev"]/math.sqrt(n))
            ptile = z_to_pct(-abs(zscore))
            r[k] = ptile
    return r

def randtest(rand, p, pval):
    if isinstance(p, list):
        return randtestall(rand, p, pval)

    length = rand["length"]

    if len(p) != length:
        raise ValueError("Input stats block length is different than test block length")

    if type(p) != bytes and type(p) != bytearray:
        raise ValueError("Input stats block must be bytes")

    r = randstats(p)
    pct = zptiles(rand, r)
    pval = pval
    bonf = len(pct)
    evidence = []
    for k, v in pct.items():
        v *= bonf
        if v < pval:
            evidence.append((k, v))
    return evidence

def randtestall(rand, points, pval):
    length = rand["length"]

    d={}
    for p in points:
        if len(p) != length:
           raise ValueError("Input stats block length is different than test block length")

        if type(p) != bytes and type(p) != bytearray:
            raise ValueError("Input stats block must be bytes")

        r = randstats(p)

        for k, v in r.items():
            if k not in d:
                d[k] = Statistics()
            d[k].push(v)

    # use sample mean values instead
    for k,v in d.items():
        if k == "count":
            d[k] = len(v)
        d[k] = v.mean()

    # test using means
    pct = zptiles(rand, d, len(d))
    pval = pval
    bonf = len(pct)
    evidence = []
    for k, v in pct.items():
        v *= bonf
        if v < pval:
            evidence.append((k, v))
    return evidence

def loadstats(length=None, file=None, dir=None):
    if file is None:
        if length is None:
            raise TypeError("Specify a file or length")
        file = f"urandom.{length}.stats"
        if dir:
            file = os.path.join(dir, file) 
    elif dir:
        raise TypeError("dir only used with length param")

    ret = json.load(open(file, "rb"))
    if length:
        if ret["length"] != length:
            raise TypeError("length mismatch loading stats")

    assert ret["length"]

    return ret

def main():
    import argparse
    parser = argparse.ArgumentParser(description='test random bytes')
    parser.add_argument("-b", "--build", action="store_true")
    parser.add_argument("-f", "--file", action="store")
    parser.add_argument("-a", "--all", action="store")
    parser.add_argument("-s", "--stats", action="store", default=None)
    parser.add_argument("-p", "--pval", action="store", default=0.05)
    parser.add_argument("-i", "--iter", action="store", default=1000, type=int)
    parser.add_argument("-l", "--length", action="store", type=int, default=1024)
    args = parser.parse_args()

    if args.stats is None:
        args.stats = f"urandom.{args.length}.stats"

    if args.build:
        buildstats(args.length, args.iter, lambda d: os.urandom(d), file=args.stats)

    if args.file:
        rand = loadstats(file=args.stats)
        with open(args.file, "rb") as f:
            ev = randtest(rand, f.read(args.length), args.pval)
            for k, v in ev:
                print("not random:", k, "pval==", v)
            if ev:
                sys.exit(1)

    if args.all:
        rand = loadstats(args.stats)
        with open(args.all, "rb") as f:
            def pgen():
                while True:
                    d = f.read(args.length)
                    if len(d) != args.length:
                        return
                    yield d

            ev = randtestall(rand, pgen(), args.pval)
            for k, v in ev:
                print("not random:", k, "pval==", v)
            if ev:
                import sys
                sys.exit(1)

from unittest import TestCase

# since we're using real random nubmers
# this will fail some small (1e-20)% of the time
# todo: switch to using a seeded prng, so it can't fail so easily

class TestIsRand(TestCase):
    @classmethod
    def setUpClass(self):
        self.stats8 = buildstats(8, 1000, os.urandom)
        self.stats16 = buildstats(16, 500, os.urandom, file="test-stats16.json")

    def test_load(self):
        st = json.load(open("test-stats16.json", "rb"))
        self.assertEqual(st,self.stats16)

    def test_use(self):
        # 8 byte random number sequences
        oks = []
        for i in range(80):
            probably_ok = os.urandom(8)
            notrand = randtest(self.stats8, probably_ok, 0.05)
            oks.append(not notrand)
        self.assertGreater(sum(oks), 60)

    def test_fixedbit(self):
        oks = []
        for i in range(20):
            randy = bytearray(os.urandom(8))
            # fixed bit per byte
            for i, b in enumerate(randy):
                randy[i] = b & 0x01
            notrand = randtest(self.stats8, randy, 0.05)
            oks.append(not notrand)
        self.assertLess(sum(oks), 2)

    def test_sequence(self):
        # 8 byte sequences not ok
        oks = []
        for i in range(20):
            randy = bytes(range(i, i+40, 5))
            notrand = randtest(self.stats8, randy, 0.05)
            oks.append(not notrand)
        self.assertLess(sum(oks), 2)

    def test_onebit(self):
        # single bit bad per sequence
        oks = []
        for i in range(20):
            randy = bytearray(os.urandom(16))
            # fixed bit per sequence
            randy[0] = randy[0] & 0x01
            notrand = randtest(self.stats16, randy, 0.05)
            oks.append(not notrand)
        self.assertLess(sum(oks), 2)

if __name__ == "__main__":
    main()

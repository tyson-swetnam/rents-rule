# Origin: the August 2026 email exchange

The project began with this exchange. Email addresses and signature boilerplate have been
removed; the scientific content is verbatim. Bold annotations in brackets are editorial
pointers to where each thread is picked up in this repository.

---

## Melanie Moses → Tyson Swetnam, cc Matthew Fricke — Saturday, August 22, 2026

**Subject: Scaling and data centers**

Hi Tyson! (cc'ing Matthew)

I was very happy to hear about your prior work with Brian Enquist and interest in scaling
theory. As I mentioned, I've been working on a project outlining how metabolic scaling
theory suggests size tradeoffs for data centers. Thus far we suspect both increasing and
diminishing returns to scale for different factors. Traditionally, compute has increasing
returns to scale, although that is less certain with the end of Moore's Law and Dennard
scaling. Cooling and power may face diminishing returns. Rent's Rule is a pattern that
provides a path to linear returns to scale - communication locality can result in linear
communication cost as a system size increases, as long as the fractions of distant vs
local communication remain fixed inverses of the distances communicated.
**[→ topics/05-returns-to-scale]**

A first question is: do communication infrastructure and communication patterns follow
Rent's Rule in data centers? We are looking for the ratio of communication paths (wires,
interconnect) from a module vs the number of transistors inside that module, where a
module could be a chip, server, rack, row of racks, etc, inside a datacenter.
**[→ topics/01-rents-rule-hardware]**

Hardware question: At multiple scales (e.g., GPU or CPU, server, rack, pod, data center),
what is the ratio of communication 'wires' or interconnect to number of transistors at
that level of organization?

Eg if a GPU has 1 billion transistors and 1000 wires connecting to other GPUs, and a rack
has 1 trillion transistors, does it have 1000 times more wires? If it's nonlinear, what is
the relationship between compute capacity within a module and communication capacity
outside that module? We would be interested in knowing this at any scale you could measure
it.

Software question, first focusing on inference loads: How much communication is there over
the wires at each scale (i.e., between compute nodes, between servers, between racks, etc.)
under load? How much does this vary?
**[→ topics/02-communication-locality-under-load]**

These are both ways of asking how much communication locality is there in a data center.
Is this a question you already monitor and optimize, or one of potential interest in
optimizing data center designs?

I'm also interested in looking at scaling relationships with other networks that serve
data centers, esp power and cooling, and how they change with scale. We are looking for
data from smaller scale centers like CARC, and also talking to larger centers - larger
universities, NAIRR, hyperscalers. Would you be interested in talking about this sometime
next week?
**[→ topics/04-power-and-cooling-networks]**

Thanks!

Melanie

---

## Tyson Swetnam → Melanie Moses — reply

Hi Melanie,

Yes, this is an exciting idea, happy to talk about it soon. Some of this is outside of my
focus for a while now, so I'll be playing a bit of catch up here.

Re: hardware scaling (cpu, gpu, interconnects) — transistors and wires do not scale
one-to-one within a server, e.g., an NVIDIA DGX SuperPod has many GPUs to external wires
(lots of intra-server communication). Transistor to copper or optical wire counts do not
account for "bandwidth," usually what is measured. There's different amounts of
information passing amongst and across the silicon (cpu, gpu, interconnects) and wires
that depends on the network topology (where are the data, databases, computing, inferences
all taking place??).
**[→ topics/01 §"wires vs bandwidth"; hardware/reference/link_bandwidths.csv]**

1/f spectral frequencies are how ethernet traffic is classically measured (Hurst exponents
from Mandelbrot) and exhibit strong scaling with known exponents.
**[→ topics/03-traffic-self-similarity]**

I think Rent's Rule does scale with conventional fat-tree network topologies (just like
capillaries in organisms or xylem in a tree, but that does not account for total bandwidth
(transit of information packets). A fat-tree network will have a Rent's p=1 but a p < 1 is
how far down a workload can be pushed — and I don't think anyone has ever measured
anything like this.
**[→ docs/background/fat-tree-topologies.md; the hardware-vs-workload exponent distinction]**

Re: power and cooling — I expect that data center power use efficiency (PUE) goes up with
size (and newer tech) — the newest data centers are saying they have PUE of ~1.1-1.2;
older data centers are ~1.5-1.6.
**[→ topics/04; data/reference/pue_by_facility.csv]**

Operators monitor everything in their data centers at multiple scales, but again I've
never seen anything like a Rent's exponent measured for bandwidth from the cpu -> server
-> rack -> pod -> facility -> network. If we're living in an age where data and databases
live on data lakes, and inference comes from major hyper-scalers, we have to move this
information across networks, I think that makes the questions you're asking especially
apropos.

I did some googling and found some scaling papers stating that next-gen compute will need
to be neuromorphic or at least emulate human brains to move fluid, heat, and power "in 5
dimensions" — but I couldn't get the full pdf.
https://ieeexplore.ieee.org/abstract/document/6044603
**[→ topics/06-beyond-2d-neuromorphic-5d]**

I'm fairly certain we could use a coding AI to write a set of benchmark tests to analyze
our own Rent's exponents across CARC and the other resources we have available to us. From
my naive searches, nobody has done this yet.
**[→ benchmarks/, telemetry/, docs/02-measurement-plan.md]**

I'm out chasing deer on the Arizona Strip (western N Rim of the Grand Canyon) for the next
two weeks. I can do Starlink calls during the day but may be interrupted if my luck
changes.

PS — here's my languished project inspired by Brian, Geoff, and Jim's fractal paper:
https://tyson-swetnam.github.io/fractal-notebooks/

Tyson L. Swetnam, Ph.D.
Director, Center for Advanced Research Computing (CARC)
Associate Professor, Department of Computer Science
University of New Mexico

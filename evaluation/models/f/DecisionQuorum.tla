---------------------------- MODULE DecisionQuorum ----------------------------
(* C-F1 finite model, PAPER-DERIVED RECONSTRUCTION. Four witnesses, threshold Q, a set Byz of
   Byzantine witnesses, two conflicting decision values. Honest witnesses sign at most one value
   (persistent single-signing, controlled by Persist). A certificate for v exists when at least Q
   distinct witnesses have signed v. This checks the combinatorics of quorum overlap only. It does
   NOT model Anvil/PoS consensus, delivery, clocks, keys or the real adapter; a counterexample at
   Byz of size 2 is conditional on two Byzantine witnesses (f=2 > 1, outside the fault bound), not a measured chain break.
   Bounded exhaustive exploration is not a proof of production behaviour. *)
EXTENDS Naturals, FiniteSets

CONSTANTS W,        \* witness identities (model values)
          Byz,      \* Byzantine subset of W
          Q,        \* acceptance threshold
          Persist   \* TRUE: an honest witness never signs a second value

Values == {"a", "b"}

ASSUME /\ Byz \subseteq W
       /\ Q \in 1..Cardinality(W)
       /\ Persist \in BOOLEAN
       \* quorum intersection arithmetic: two sets of size >= Q overlap in >= 2Q-N witnesses
       /\ \A S, T \in SUBSET W :
             (Cardinality(S) >= Q /\ Cardinality(T) >= Q)
                => Cardinality(S \cap T) >= 2*Q - Cardinality(W)

VARIABLE signed   \* signed[w] = set of values w has signed

vars == signed

TypeOK == signed \in [W -> SUBSET Values]

Init == signed = [w \in W |-> {}]

HonestSign(w, v) ==
    /\ w \notin Byz
    /\ IF Persist THEN signed[w] = {} ELSE TRUE
    /\ signed' = [signed EXCEPT ![w] = @ \cup {v}]

ByzSign(w, v) ==
    /\ w \in Byz
    /\ signed' = [signed EXCEPT ![w] = @ \cup {v}]

Next == \E w \in W, v \in Values : HonestSign(w, v) \/ ByzSign(w, v)

Spec == Init /\ [][Next]_vars

Signers(v) == {w \in W : v \in signed[w]}
Certified(v) == Cardinality(Signers(v)) >= Q

\* Agreement: two conflicting values are never both certified.
Agreement == ~(Certified("a") /\ Certified("b"))

\* When Persist holds, every witness that signed both values is Byzantine. Agreement with
\* Cardinality(Byz) < 2Q-N follows from this plus the overlap ASSUME.
HonestSingle == Persist => \A w \in W \ Byz : Cardinality(signed[w]) <= 1
=============================================================================

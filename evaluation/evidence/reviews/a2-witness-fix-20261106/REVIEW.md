# Scoped review of A2-0069

Accepted: forwarding_call checks the carried Chain result is a dict before
calling tx.get. Non-object replies are LedgerUnreachable. The new AttributeError
catch is additional guard coverage; the owner explicitly excludes W46 as
indistinguishable by the exercised paths after the object check. That is an
observed testing limit, not a universal proof of semantic equivalence.

The four independent raw-RPC transaction probes reproduce AttributeError on the
old snapshot and LedgerUnreachable on the new one. The fourteen controls include
canonical block/ABI successes, missing transaction/block distinctions, undecodable
call None, wrong chain and explicit transport/decode refusals. The 13 diagnostics
retain three accepted quantity variants (0x1_0, 0x01, 0xA) and two accepted ABI
variants (trailing word, nonhex prefix). These five observations now match the
view's documented permissive-codec limit; canonical witness bytes remain unproved.
Negative/signed/whitespace quantities and an integer ABI result are refused,
preserving four refuted suspicions. No incorrect authorization is demonstrated.

The owner property loop substitutes eight junk values across sixteen methods and
checks for unexpected exceptions. It does not assert returned object shapes;
its prose description is stronger than that loop's actual assertions. The
specific new transaction tests do assert refusal/None/returned-key alternatives.
The independent raw probes support only the methods/replies actually exercised.
This is a coverage limitation, not a newly demonstrated correctness failure.

Both newly effective mutations are detected: W45 removes object validation;
W47 misclassifies a non-object as a quiet None. The retained owner run1 44/46 and
historical red/green receipts were read/hash-pinned, not independently recreated.
Fresh full focused mutation runner detects45/45 and its control passes. The
owner's61 combined unit/live result is not adopted; this review executes no live
file and starts no node. Existing no-live setup guard and selector are reused.

Docstrings now distinguish missing transactions from undecodable calls and limit
the real-contract decision/receipt statement to the owner's honest-path trial.
Carried latest-state reads remain unpinned to observe; NUMBER reads have no
reorg/EIP-1898 guarantee. Documenting permissive codecs does not establish native
truth, canonicality, completeness or sign-time consistency. RpcBindingView's
previous separate strict-parser closure remains unchanged.

No product/interface/peer module bytes changed. Full Worker factory, CLI with
exact published schema and check_responses=True plus valid handlers, supervised
witnesses, real transport/clock and H2/H5/H6 remain pending. Complete runtime
READY and separate exact execution FREEZE ACKs still precede services/scenarios.
This scoped review closes A3-0093's transaction/error-prose request only.

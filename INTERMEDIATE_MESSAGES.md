# Vole-PSI Protocol Intermediate Files (`.txt` / `.bin`)

When you run the `frontend` using the `-file-passing` flag, the program captures and writes all messages sent through the protocol buffer into sequential files. 

* The `.bin` files contain the literal binary bytes processed by the `coproto` networking socket.
* The `.txt` files are your human-readable hexadecimal dumps of exactly the same bytes.

Because `coproto::BufferingSocket` flushes the socket whenever the coroutine suspends to wait for network I/O, these files roughly correspond to the "communication rounds" of the **Vector-OLE based Private Set Intersection (VOLE-PSI)** protocol.

Here is a breakdown of what the hexadecimal payloads inside these files actually represent.

---

## 1. Initial Setup & Base OTs (`sender_0.txt`, `recver_0.txt`)
**What's inside:** Random seeds, protocol handshakes, and Elliptic Curve Points.
* **Why:** Before the PSI protocol can run, the two parties need to establish foundational "Base Oblivious Transfers" (Base OTs). If you look at the hex values here, you are primarily seeing the serialization of public keys used in the Diffie-Hellman / Elliptic Curve setup (via `libsodium`), along with randomly chosen secure PRNG seeds used to synchronize matrices later.

## 2. VOLE Extension & LPN (`sender_1.txt`, `recver_1.txt`, etc.)
**What's inside:** Learning Parity with Noise (LPN) correction matrices and Vector OLE choices.
* **Why:** OTs are computationally expensive. The protocol expands a few Base OTs into millions of OTs using a post-quantum LPN assumption (typically using Quasi-Cyclic matrices as enabled by `-useQC`). The receiver sends over correction bits corresponding to their choices so that the sender can blindly evaluate the LPN matrix logic. What you see in these text files are large, highly-randomized dense bit-vectors representing the LPN error and correction sequences.

## 3. Oblivious PRF (OPPRF) via OKVS (`recver_X.txt`)
**What's inside:** The Baxos/Paxos Oblivious Key-Value Store (OKVS) structure.
* **Why:** The Receiver hashes their input dataset (e.g. from `receiver_set.csv`) and encodes the resulting rules into an OKVS—a purely linear-algebraic structure where finding an element means solving random linear equations. The hex dump in this phase represents the solved OKVS rows (or polynomial coefficients). Because it's an OKVS, the payload mathematically masks the receiver's real dataset while allowing the Sender to conditionally evaluate the PRF only on valid matching items.

## 4. The PSI Filter (`sender_X.txt`)
**What's inside:** The Sender's randomized OPRF evaluation (often in a Cuckoo filter, Bloom filter, or secondary OKVS).
* **Why:** Once the Sender processes the Receiver's OKVS, they apply the Vector OLE correlations to their own dataset (from `sender_set.csv`). They send back hashes of their items under this newly established Oblivious Pseudo-Random Function. The hex chunk you see here consists of the densely packed, permuted evaluation values. The Receiver will check these values against their own local computations to natively derive the final intersection list.

---

### Understanding the Hex
If you open one of these `.txt` files, the format is printed as 32 hex bytes per line:
`d8a9463b2100...`

While inspecting, note that due to cryptographic masking (Random Oracles, AES/SHA hashes, and LPN), these buffers should perfectly resemble high-entropy randomness (white noise). You will not find any plaintext rows of your `sender_set.csv` or `receiver_set.csv`—this is the core mathematical guarantee of the Vole-PSI protocol!

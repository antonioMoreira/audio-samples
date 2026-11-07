# PCM-16 `WAV` vs. `FLAC`: Losslessness, Storage, and Real-Time Streaming

This document summarizes our evaluation of converting 16-bit integer PCM (`pcm_s16le`) `.wav` audio files to `.flac` and back (`WAV -> FLAC -> WAV`), how data loss is measured, benchmark findings from [`benches/wav_to_flac_bench.py`](../benches/wav_to_flac_bench.py), and when to prefer `WAV` over `FLAC` (including real-time streaming vs. batch transport).

---

## 1. Is `WAV -> FLAC -> WAV` Lossless?

**Yes — 100% bit-exact lossless** for integer PCM formats (`pcm_s16le`).

FLAC (*Free Lossless Audio Codec*) compresses integer PCM samples using linear predictive coding (LPC) and Rice residual coding without quantization. When decoded back to `s16` (or re-packaged into a `pcm_s16le` `.wav` container), the reconstructed sample sequence $z[n]$ is **bit-for-bit identical** to the original sample sequence $x[n]$.

### How Data Loss Is Measured

In [`benches/wav_to_flac_bench.py`](../benches/wav_to_flac_bench.py), equivalence is verified across four levels between the original WAV $x[n]$, the intermediate FLAC $y[n]$, and the re-converted WAV $z[n]$:

1. **Stream & Structural Metadata Parity**:
   - Sample rate ($\text{Hz}$), channel count, sample format (`s16`), and total decoded sample count must match identically:
     $$N_{\text{wav}} = N_{\text{flac}} = N_{\text{re\_wav}}$$
2. **Bit-Exact Raw `int16` & Cryptographic Hash Equality**:
   - Element-wise array equality on decoded `np.int16` buffers: `np.array_equal(x_int16, y_int16)` and `np.array_equal(x_int16, z_int16)`.
   - Mismatched sample count: $\sum_{n=1}^{N} \mathbb{I}(x[n] \neq z[n]) = 0$.
   - SHA-256 digest equality of raw PCM bytes:
     $$\text{SHA256}(x_{\text{int16}}) = \text{SHA256}(y_{\text{int16}}) = \text{SHA256}(z_{\text{int16}})$$
3. **Numerical Reconstruction Error Metrics (`int16` and normalized `float32`)**:
   - **Maximum Absolute Error ($L_\infty$)**: $\max_n |x[n] - z[n]| = 0$
   - **Mean Absolute Error (MAE)**: $\frac{1}{N}\sum_{n=1}^N |x[n] - z[n]| = 0.0$
   - **Root Mean Squared Error (RMSE)**: $\sqrt{\frac{1}{N}\sum_{n=1}^N (x[n] - z[n])^2} = 0.0$
   - **Signal-to-Noise Ratio (SNR)**: $10 \log_{10}(P_{\text{signal}} / P_{\text{error}}) = +\infty\text{ dB}$
4. **Container File Byte Comparison**:
   - Compares the raw on-disk file bytes of the original `.wav` and re-converted `.wav` (`wav_path.read_bytes() == re_wav_path.read_bytes()`).

---

## 2. Benchmark Results (`output/samples_agro1/30`)

Running `uv run benches/wav_to_flac_bench.py` on twenty 30-second `16 kHz` mono `pcm_s16le` `.wav` chunks (`480,000` samples per file, `9,600,000` samples total):

| Metric | Result |
| :--- | :--- |
| **Single 30s WAV Size** | `937.58 KB` (`960,078 bytes`) |
| **Single 30s FLAC Size** | `347 KB – 601 KB` (`~418 KB` average) |
| **Total Original WAV Size (20 files)** | `18.31 MB` (`19,201,560 bytes`) |
| **Total Intermediate FLAC Size (20 files)** | `8.17 MB` (`8,569,784 bytes`) |
| **Total Re-converted WAV Size (20 files)** | `18.31 MB` (`19,201,560 bytes`) |
| **Space Saved / Compression Ratio** | **`55.37%` saved (`2.24x` compression)** |
| **Mismatched PCM Samples (`WAV -> FLAC -> WAV`)** | **`0 / 9,600,000`** (`MaxErr = 0`, `SHA256 = MATCH`) |
| **Exact Container Byte Matches (`WAV == Re-WAV`)** | **`20 / 20` files (`+0 bytes` diff)** |
| **Mean `WAV -> FLAC` Encode Time (per 30s file)** | `~20.0 ms` |
| **Mean `FLAC -> WAV` Decode Time (per 30s file)** | `~7.3 ms` |

---

## 3. When to Prefer `WAV` Over `FLAC`

Even though `FLAC` is lossless and ~55–60% smaller, **`WAV` (`pcm_s16le` / `pcm_f32le`) is preferred in the following scenarios**:

### 3.1 Zero-Copy / Memory-Mapped Random Access (`mmap`)
- **WAV** stores uncompressed samples contiguously immediately after a fixed header (44–78 bytes).
  - Seeking to any exact sample index $k$ is **$O(1)$** via byte-offset arithmetic (`header_size + k * 2`).
  - Large files can be memory-mapped (`np.memmap`) with zero RAM overhead and sliced without decoding earlier audio.
- **FLAC** uses variable-length compressed frames. Seeking requires parsing seek tables and decoding the enclosing FLAC frame.

### 3.2 CPU-Bound ML Data Loading on Fast Local NVMe SSDs
- Reading raw PCM from local NVMe or RAM disk is a pure memory copy with near-zero CPU cost.
- When training models over many epochs on a fast GPU where the CPU dataloader is the bottleneck and local SSD space is abundant, uncompressed `.wav` avoids spending CPU cycles decompressing FLAC every epoch.

### 3.3 32-Bit Floating-Point Audio (`pcm_f32le`)
- **WAV** natively supports 32-bit and 64-bit IEEE floating-point PCM (`pcm_f32le`), which is standard in intermediate DSP pipelines and audio synthesis.
- **FLAC** is strictly an **integer** codec (up to 24/32-bit integer PCM). Converting `float32` WAV to `int16`/`int24` FLAC introduces quantization/clipping loss.

### 3.4 Universal Low-Level & Embedded Compatibility
- Raw WAV requires no codec library (`libFLAC` / `FFmpeg`); it can be read/written with Python's standard library `wave` module, microcontrollers without FPUs, or browser `AudioContext` buffers in a few lines of code.

---

## 4. Real-Time Streaming vs. Batch Network Traffic

Although a `.flac` file is smaller than a `.wav` file, **raw PCM (`wav` / `s16le`) is usually superior for real-time speech streaming** (such as live ASR / `faster-whisper`):

### 4.1 Why Raw PCM (`s16le`) Wins in Real-Time Streams
1. **Zero Algorithmic Buffering Latency**:
   - **FLAC is block-based**: By default, FLAC encodes blocks of `4,096` samples. At `16 kHz`, the encoder must wait **$4096 / 16000 = 256\text{ ms}$** just to fill a single block before it can compress and transmit a frame.
   - **Raw PCM has $0\text{ ms}$ codec delay**: `10–20 ms` chunks (`320–640 bytes`) can be transmitted immediately as samples arrive from the microphone.
2. **16 kHz Mono Bandwidth Is Already Small**:
   - Uncompressed `16 kHz`, `16-bit`, `mono` audio uses only:
     $$16{,}000 \text{ samples/s} \times 2 \text{ bytes} = \mathbf{32\text{ KB/s}} \text{ (256 kbps)}$$
   - Reducing `32 KB/s` to `~14 KB/s` with FLAC rarely matters on LAN/broadband/datacenter links, whereas adding `256 ms` of buffering latency degrades interactive voice responsiveness.
3. **Arbitrary Ring-Buffer Slicing & Packet-Loss Resilience**:
   - Every 2 bytes in a raw `s16le` stream is a self-contained sample. The receiver can append incoming bytes directly into a ring buffer and run VAD or Whisper on any window immediately without maintaining a stateful frame decoder.

### 4.2 When FLAC (or Opus) Wins on the Network
- **Batch Chunk Uploads (HTTP / REST / Object Storage)**:
  - Once a `10s` or `30s` chunk is already recorded, there is no real-time buffering penalty. Encoding to **FLAC** takes only `~20 ms` and shrinks the payload by **~55–60%** (`938 KB` $\rightarrow$ `~400 KB`), cutting upload time and storage cost in half with zero loss.
- **Bandwidth-Constrained Real-Time Streaming**:
  - When real-time bandwidth is constrained (e.g., mobile WebRTC), use **Opus** (not WAV or FLAC), which is engineered for `5–20 ms` low-latency frames at `16–32 kbps`.

---

## 5. Summary Decision Matrix

| Scenario | Recommended Format | Primary Reason |
| :--- | :--- | :--- |
| **Dataset archival, Git repo, S3/cloud storage** | **`FLAC`** | **~55–60% smaller**, 100% bit-exact lossless. |
| **Batch API upload of pre-sliced chunks (10s–30s)** | **`FLAC`** | Halves network payload size for only ~20 ms encode cost. |
| **Real-time low-latency ASR streaming (LAN / WebSocket / gRPC)** | **Raw PCM (`WAV` / `s16le`)** | **$0\text{ ms}$ framing latency**, trivial ring-buffer slicing, only `32 KB/s` at 16 kHz. |
| **Fast local SSD random-access slicing / `mmap`** | **`WAV`** | $O(1)$ byte-offset seeking and zero CPU decode overhead. |
| **32-bit float DSP / intermediate synthesis** | **`WAV` (`pcm_f32le`)** | FLAC only supports integer PCM. |

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import io
    import gc
    from pathlib import Path
    from typing import Annotated

    import av
    from av.audio.resampler import AudioResampler
    import numpy as np
    import numpy.typing as npt
    import matplotlib.pyplot as plt
    import torch
    from torchaudio.transforms import Loudness

    from audio_samples.utils import decode_audio
    from audio_samples.utils import _ignore_invalid_frames as ignore_invalid_frames
    from audio_samples.utils import _group_frames as group_frames
    from audio_samples.utils import _resample_frames as resample_frames

    ABS_MIN_INT = abs(np.iinfo(np.int16).min)

    # jaxtyping (De-Facto Standard for ML Codebases)
    # Despite the name, jaxtyping does not require JAX.
    type Float32Tensor = Annotated[torch.Tensor, torch.float32]
    type Int64Tensor = Annotated[torch.Tensor, torch.int64]
    return Float32Tensor, Loudness, Path, decode_audio, np, npt, torch


@app.cell
def _(Path, decode_audio):
    from sympy.physics.units import au
    audio_path = Path(
        "/mnt/antonioSSD/audio-samples/samples/traducao_e_legendagem-A_IA_TA_AI/30/150-180.wav"
        #"/mnt/disks/disk2/LibriVAD/Results/LibriSpeech/dev-clean/Babble_noise/-5/2277-149896-0009.wav"
    )

    with open(audio_path, 'rb') as f:
        audio_array = decode_audio(f)
    return (audio_array,)


@app.cell
def _(Float32Tensor, torch):
    # Note: Unlike numpy's `npt.NDArray[np.float32]`, `torch.Tensor` is not subscriptable.
    # Standard practice is to use `torch.Tensor` (or `torch.FloatTensor` to specify 32-bit float,
    # or `jaxtyping.Float[torch.Tensor, "samples"]` if using jaxtyping).
    def generate_sine_wave(
        amplitude: float = 0.5,
        frequency: float = 1000.0,
        duration_sec: int = 30,
        sample_rate: int = 16_000,
    ) -> Float32Tensor:
        """Generates a 1D sine wave tensor with a given amplitude."""
        t = torch.linspace(0, duration_sec, int(sample_rate * duration_sec), dtype=torch.float32)
        return amplitude * torch.sin(2 * torch.pi * frequency * t)

    generate_sine_wave(amplitude=1, frequency=1000.0)
    return


@app.cell
def _(Loudness, audio_array, np, npt, torch):
    def get_loudness(
        audio: npt.NDArray[np.float32], sample_rate: int = 16_000
    ) -> dict[str, float]:
        """Calculates the loudness of mono audio using RMS and LUFS.

        Args:
          audio: A float Numpy array normalized to [-1.0, 1.0] (full scale = 1.0).
          sample_rate: The sampling rate of `audio` in Hz.

        Returns:
          A dict with:
            rms: The linear RMS amplitude.
            rms_dbfs: The RMS level in dBFS (20 * log10(rms), 0 dBFS = full scale).
            lufs: The integrated loudness in LUFS (ITU-R BS.1770-4, K-weighted and
              gated), which is relative to full scale.
        """
        audio = np.asarray(audio, dtype=np.float32)
        rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
        rms_dbfs = 20 * np.log10(max(rms, 1e-10))

        lufs = Loudness(sample_rate)(torch.from_numpy(audio).unsqueeze(0)).item()
        if np.isnan(lufs):  # Silence (or shorter than 400 ms) has no gated blocks.
            lufs = -np.inf

        return {"rms": rms, "rms_dbfs": float(rms_dbfs), "lufs": float(lufs)}

    get_loudness(audio_array)
    return


if __name__ == "__main__":
    app.run()

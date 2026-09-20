# Source Generated with Decompyle++
# File: audio.pyc (Python 3.12)

'''Audio I/O helpers — plain numpy + soundfile/scipy, no torch.'''
from __future__ import annotations
from math import gcd
import numpy as np
SAMPLE_RATE = 48000

def load_wav_mono(path = None, target_sr = None):
    '''Load a wav, downmix to mono, resample to ``target_sr``. Returns (T,) float32.'''
    import soundfile as sf
    (wav, sr) = sf.read(path, always_2d = True)
    wav = wav.mean(axis = 1).astype(np.float32)
    if sr != target_sr:
        resample_poly = resample_poly
        import scipy.signal
        g = gcd(target_sr, sr)
        wav = resample_poly(wav, target_sr // g, sr // g)
    return wav.astype(np.float32)


def resample_wav(wav = None, sr_from = None, sr_to = None):
    """Resample a 1-D float32 array, matching load_wav_mono's resampler."""
    if sr_from == sr_to:
        return wav.astype(np.float32)
    resample_poly = resample_poly
    import scipy.signal
    g = gcd(sr_from, sr_to)
    return resample_poly(wav, sr_to // g, sr_from // g).astype(np.float32)


def save_wav(audio = None, path = None, sample_rate = None):
    '''Save a (..., T) float array (leading dims squeezed) as 16-bit PCM wav.'''
    import soundfile as sf
    sf.write(path, np.asarray(audio).squeeze(), sample_rate, subtype = 'PCM_16')


def concat_with_silence(chunks = None, silence_sec = None, sample_rate = None):
    '''Join (1, T) or (T,) chunks with ``silence_sec`` of silence between them.'''
    pass
# WARNING: Decompyle incomplete


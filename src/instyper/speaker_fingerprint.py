from pathlib import Path
from typing import Optional
import json
try:
    import numpy as np
except Exception:
    np = None

try:
    from python_speech_features import mfcc
except Exception:
    mfcc = None

try:
    from cryptography.fernet import Fernet
except Exception:
    Fernet = None

try:
    from scipy.fftpack import dct as _scipy_dct
except Exception:
    _scipy_dct = None


DEFAULT_SIG_PATH = Path.home() / '.instyper' / 'speaker.sig'


def _compute_mfcc_fallback(wave: np.ndarray, sr: int = 16000, numcep: int = 13):
    """A minimal MFCC fallback using numpy. Not as feature-complete as python_speech_features."""
    if np is None:
        raise ImportError('numpy is required for MFCC computation (install numpy).')
    try:
        # simple framing params
        frame_len = int(0.025 * sr)
        frame_step = int(0.01 * sr)
        signal_length = len(wave)
        num_frames = 1 + int((signal_length - frame_len) / frame_step) if signal_length > frame_len else 1
        pad_len = int((num_frames - 1) * frame_step + frame_len)
        z = np.zeros((pad_len - signal_length,))
        signal = np.concatenate((wave, z))

        indices = np.tile(np.arange(0, frame_len), (num_frames, 1)) + np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_len, 1)).T
        frames = signal[indices.astype(np.int32, copy=False)]
        frames *= np.hamming(frame_len)
        mag_frames = np.absolute(np.fft.rfft(frames, n=512))
        pow_frames = ((1.0 / 512) * (mag_frames ** 2))
        fbanks = np.log(np.maximum(pow_frames, 1e-12))
        # take dct of filter banks
        # use scipy's dct if available
        if _scipy_dct is not None:
            cep = _scipy_dct(fbanks, type=2, axis=1, norm='ortho')[:, :numcep]
        else:
            # simple numpy-based dct (slower, less accurate) fallback
            def _dct(x):
                # naive DCT-II for small arrays
                return np.real(np.fft.fft(np.concatenate([x, x[::-1]], axis=1)))
            cep = _dct(fbanks)[:, :numcep]
        return cep
    except Exception:
        return np.zeros((1, numcep))


def compute_mfcc(wave: np.ndarray, sr: int = 16000, numcep: int = 13) -> np.ndarray:
    """Compute MFCC features for given audio waveform (numpy array, float32 or int16).

    Returns shape (n_frames, numcep)
    """
    if np is None:
        raise ImportError('numpy is required for MFCC computation (install numpy).')
    if mfcc is not None:
        try:
            # python_speech_features mfcc expects 16-bit PCM values or floats
            return np.array(mfcc(wave, samplerate=sr, numcep=numcep))
        except Exception:
            pass
    return _compute_mfcc_fallback(wave, sr=sr, numcep=numcep)


def aggregate_signature(mfcc_feats: np.ndarray) -> np.ndarray:
    """Aggregate MFCC frames to a normalized signature vector (mean-normalized).

    Returns 1D numpy array
    """
    if mfcc_feats is None or len(mfcc_feats) == 0:
        return np.zeros((mfcc_feats.shape[1],)) if mfcc_feats is not None else np.zeros((13,))
    v = np.mean(mfcc_feats, axis=0)
    norm = np.linalg.norm(v)
    if norm < 1e-9:
        return v
    return (v / norm).astype(np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    try:
        a = np.array(a, dtype=np.float32)
        b = np.array(b, dtype=np.float32)
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
        return float(np.dot(a, b) / denom)
    except Exception:
        return 0.0


def save_signature(sig: np.ndarray, path: Optional[Path] = None, key: Optional[bytes] = None) -> None:
    p = Path(path or DEFAULT_SIG_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {'sig': sig.tolist()}
    raw = json.dumps(data).encode('utf-8')
    if Fernet is not None and key is not None:
        try:
            f = Fernet(key)
            raw = f.encrypt(raw)
        except Exception:
            pass
    p.write_bytes(raw)


def load_signature(path: Optional[Path] = None, key: Optional[bytes] = None) -> Optional[np.ndarray]:
    p = Path(path or DEFAULT_SIG_PATH)
    if not p.exists():
        return None
    raw = p.read_bytes()
    if Fernet is not None and key is not None:
        try:
            f = Fernet(key)
            raw = f.decrypt(raw)
        except Exception:
            pass
    try:
        data = json.loads(raw.decode('utf-8'))
        return np.array(data.get('sig', []), dtype=np.float32)
    except Exception:
        return None


def enroll_from_wave(wave: np.ndarray, sr: int = 16000, numcep: int = 13, path: Optional[Path] = None, key: Optional[bytes] = None) -> np.ndarray:
    feats = compute_mfcc(wave, sr=sr, numcep=numcep)
    sig = aggregate_signature(feats)
    save_signature(sig, path=path, key=key)
    return sig


def verify_wave(wave: np.ndarray, enrolled: np.ndarray, sr: int = 16000, numcep: int = 13, threshold: float = 0.78) -> bool:
    if enrolled is None:
        return False
    feats = compute_mfcc(wave, sr=sr, numcep=numcep)
    sig = aggregate_signature(feats)
    sim = cosine_similarity(sig, enrolled)
    return sim >= float(threshold) 

def _read_wav_to_np(wav_path: str) -> np.ndarray:
    """Read a WAV file from disk and return a 1-D numpy float32 array (mono).

    This is a minimal, dependency-light reader that supports 16-bit PCM.
    """
    import wave as _wave
    if np is None:
        raise ImportError('numpy is required for WAV reading')
    try:
        with _wave.open(wav_path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
    except Exception:
        raise

    # Currently only handle 16-bit PCM reasonably
    if sampwidth == 2:
        dtype = np.int16
    else:
        # Best-effort fallback
        dtype = np.int16
    arr = np.frombuffer(raw, dtype=dtype)
    if n_channels > 1:
        try:
            arr = arr.reshape(-1, n_channels)[:, 0]
        except Exception:
            arr = arr
    # Convert to float32 in range [-1, 1]
    arr = arr.astype(np.float32) / 32768.0
    return arr


def enroll_speaker(wav_path: str, sr: int = 16000, numcep: int = 13, path: Optional[Path] = None, key: Optional[bytes] = None) -> Optional[str]:
    """Enroll a speaker from a WAV file path.

    This reads the WAV, computes a signature and persists it to disk (DEFAULT_SIG_PATH
    unless `path` is provided). Returns a short speaker id string on success or None.
    """
    try:
        wave_arr = _read_wav_to_np(wav_path)
    except Exception:
        return None
    try:
        sig = enroll_from_wave(wave_arr, sr=sr, numcep=numcep, path=path or DEFAULT_SIG_PATH, key=key)
        # Produce a short, reproducible id for UI display
        import hashlib
        sid = hashlib.sha1(sig.tobytes()).hexdigest()[:8]
        return sid
    except Exception:
        return None


def verify_file(wav_path: str, enrolled: Optional[np.ndarray] = None, sr: int = 16000, numcep: int = 13, threshold: float = 0.78) -> bool:
    """Verify a WAV file against an enrolled signature.

    If `enrolled` is None this will attempt to load the signature from the default
    signature file. Returns True when the WAV matches the enrolled speaker.
    """
    try:
        if enrolled is None:
            enrolled = load_signature(path=DEFAULT_SIG_PATH)
        if enrolled is None:
            # No enrolled signature available
            return False
        wave_arr = _read_wav_to_np(wav_path)
        return verify_wave(wave_arr, enrolled, sr=sr, numcep=numcep, threshold=threshold)
    except Exception:
        # On errors, return False (do not allow unknown/erroneous audio)
        return False
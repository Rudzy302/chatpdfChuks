"""Servicio de generación y sintetización de audio, efectos de sonido y canciones con IA."""

import os
import re
import hashlib
import urllib.request
import numpy as np
import wave
from ..config import settings

AUDIOS_DIR = os.path.join(settings.UPLOADS_DIR, "generated_audio")
os.makedirs(AUDIOS_DIR, exist_ok=True)

# Catálogo curado de efectos de sonido auténticos de alta fidelidad (Wikimedia Commons Special:FilePath)
SFX_CATALOG = {
    "perro": {
        "title": "Ladrido de Perro Auténtico",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Barking_of_a_dog.ogg",
        "type": "ogg"
    },
    "ladrido": {
        "title": "Ladrido de Perro Auténtico",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Barking_of_a_dog.ogg",
        "type": "ogg"
    },
    "gato": {
        "title": "Maullido de Gato",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Cat_Meow_2.ogg",
        "type": "ogg"
    },
    "maullido": {
        "title": "Maullido de Gato",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Cat_Meow_2.ogg",
        "type": "ogg"
    },
    "lluvia": {
        "title": "Sonido de Lluvia y Tormenta",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Rain_on_glass_sound.ogg",
        "type": "ogg"
    },
    "trueno": {
        "title": "Trueno y Rayo Retumbante",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Thunder-and-lightning-short.ogg",
        "type": "ogg"
    },
    "pajaro": {
        "title": "Canto de Aves Silvestres",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Blackbird_song.ogg",
        "type": "ogg"
    },
    "ave": {
        "title": "Canto de Aves Silvestres",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Blackbird_song.ogg",
        "type": "ogg"
    },
    "leon": {
        "title": "Rugido de León Salvaje",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Lion_roar.ogg",
        "type": "ogg"
    },
    "rugido": {
        "title": "Rugido de Fiera Salvaje",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Lion_roar.ogg",
        "type": "ogg"
    },
    "campana": {
        "title": "Campana de Iglesia / Campanario",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Church_bell_at_noon.ogg",
        "type": "ogg"
    },
    "sirena": {
        "title": "Sirena de Emergencia",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Civil_defense_siren_single_cycle.ogg",
        "type": "ogg"
    },
    "alarma": {
        "title": "Alarma Sonora",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Civil_defense_siren_single_cycle.ogg",
        "type": "ogg"
    },
    "aplauso": {
        "title": "Aplausos y Ovación del Público",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Applause_medium.ogg",
        "type": "ogg"
    },
    "mar": {
        "title": "Olas del Mar y Brisa Costera",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Ocean_waves.ogg",
        "type": "ogg"
    },
    "ola": {
        "title": "Olas del Mar y Brisa Costera",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Ocean_waves.ogg",
        "type": "ogg"
    },
    "gallo": {
        "title": "Canto de Gallo al Amanecer",
        "url": "https://commons.wikimedia.org/wiki/Special:FilePath/Rooster_crowing.ogg",
        "type": "ogg"
    }
}

def detect_audio_request(prompt: str):
    """
    Detecta si el prompt solicita la generación de un efecto de sonido, audio o una canción/música.
    Retorna (is_audio: bool, audio_type: str, subject: str)
    audio_type puede ser 'sound_effect' o 'song'.
    """
    p = prompt.strip().lower()

    # 1. Detección de canciones y música
    song_patterns = [
        r'(?:genera|crea|compon|haz|escribe|dame|canta|toca)\s+(?:una?\s+)?(?:canci[oó]n|m[uú]sica|melod[ií]a|pista|tema|beat)\s*(?:de|sobre|para)?\s*(.+)?',
        r'canci[oó]n\s+(?:de|sobre|para)\s+(.+)',
        r'm[uú]sica\s+(?:de|para|sobre)\s+(.+)',
        r'melod[ií]a\s+(?:de|para|sobre)\s+(.+)',
        r'(?:crear|generar)\s+(?:una?\s+)?(?:canci[oó]n|m[uú]sica)',
    ]
    for pat in song_patterns:
        m = re.search(pat, p)
        if m:
            subj = m.group(1).strip() if (m.groups() and m.group(1)) else "melodía armónica instrumental"
            return True, "song", subj

    # 2. Detección de efectos de sonido y audios específicos
    sfx_patterns = [
        r'(?:genera|crea|pon|reproduce|haz|dame)\s+(?:un\s+)?(?:sonido|audio|efecto\s+de\s+sonido|ruido)\s+de\s+(.+)',
        r'(?:c[oó]mo\s+suena|sonido\s+de)\s+(.+)',
        r'(?:efecto\s+de\s+sonido|audio)\s+de\s+(.+)',
        r'(?:ladrido|maullido|rugido|aullido)(?:\s+de\s+(.+))?',
    ]
    for pat in sfx_patterns:
        m = re.search(pat, p)
        if m:
            subj = m.group(1).strip() if (m.groups() and m.group(1)) else p
            return True, "sound_effect", subj

    # Palabras clave directas como "sonido de perro", "ladrido de perro"
    if any(k in p for k in ["sonido de", "efecto de sonido", "ladrido", "maullido", "rugido", "sonido de un", "audio de un"]):
        return True, "sound_effect", p

    return False, "", ""

def synthesize_procedural_sound(subject: str, filename: str) -> str:
    """Sintetiza un efecto de sonido procedimental en formato WAV estéreo/mono a 44.1kHz."""
    sr = 44100
    sub_lower = subject.lower()
    
    # Adaptar sonido según el tema
    if any(k in sub_lower for k in ["perro", "ladrido", "dog"]):
        # Ladrido acústico sintetizado (ráfagas moduladas con formantes guturales)
        duration = 1.8
        t = np.linspace(0, duration, int(sr * duration), False)
        audio = np.zeros(len(t))
        for burst_time in [0.05, 0.45, 0.95]:
            idx_start = int(burst_time * sr)
            idx_end = min(len(t), idx_start + int(0.28 * sr))
            bt = t[idx_start:idx_end] - burst_time
            # Sweep descendente de 380Hz a 180Hz con armónicos
            f0 = 380 - (bt / 0.28) * 200
            env = np.sin(np.pi * (bt / 0.28)) ** 1.5
            tone = (np.sin(2 * np.pi * f0 * bt) + 0.5 * np.sin(4 * np.pi * f0 * bt) + 0.3 * np.random.normal(0, 0.4, len(bt))) * env
            audio[idx_start:idx_end] += tone
    elif any(k in sub_lower for k in ["gato", "maullido", "cat"]):
        # Maullido (sweep tonal ascendente luego descendente con formante vocal)
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), False)
        freq_env = 450 + 350 * np.sin(np.pi * (t / duration))
        env = np.sin(np.pi * (t / duration)) ** 1.2
        audio = (np.sin(2 * np.pi * freq_env * t) + 0.4 * np.sin(4 * np.pi * freq_env * t)) * env
    elif any(k in sub_lower for k in ["trueno", "thunder", "tormenta", "lluvia"]):
        # Trueno (ruido de baja frecuencia filtrado con envolvente de explosión)
        duration = 3.5
        t = np.linspace(0, duration, int(sr * duration), False)
        noise = np.random.normal(0, 1.0, len(t))
        # Filtro pasa-bajos simple con media móvil
        window_size = 80
        filtered_noise = np.convolve(noise, np.ones(window_size)/window_size, mode='same')
        decay = np.exp(-1.2 * t) * (1.0 + 0.8 * np.sin(2 * np.pi * 1.5 * t))
        audio = filtered_noise * decay
    elif any(k in sub_lower for k in ["laser", "disparo", "futurista"]):
        # Sonido sci-fi de láser
        duration = 0.8
        t = np.linspace(0, duration, int(sr * duration), False)
        f_sweep = 2200 * np.exp(-6.0 * t)
        env = np.exp(-4.0 * t)
        audio = np.sin(2 * np.pi * f_sweep * t) * env
    else:
        # Campanilla o tono armónico agradable por defecto
        duration = 2.5
        t = np.linspace(0, duration, int(sr * duration), False)
        env = np.exp(-2.2 * t)
        audio = (
            np.sin(2 * np.pi * 523.25 * t) * 0.5 +
            np.sin(2 * np.pi * 659.25 * t) * 0.3 +
            np.sin(2 * np.pi * 783.99 * t) * 0.2
        ) * env

    # Normalizar volumen
    max_val = np.max(np.abs(audio)) + 1e-6
    audio = audio / max_val
    audio_i16 = (audio * 28000).astype(np.int16)

    out_path = os.path.join(AUDIOS_DIR, filename)
    with wave.open(out_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_i16.tobytes())

    return filename

def synthesize_procedural_song(subject: str, filename: str) -> str:
    """Sintetiza una composición musical armónica completa (melodía, acordes, bajo y percusión) en WAV a 44.1kHz."""
    sr = 44100
    duration = 10.0
    t = np.linspace(0, duration, int(sr * duration), False)
    audio = np.zeros(len(t))

    sub_lower = subject.lower()
    bpm = 110
    if any(k in sub_lower for k in ["rapida", "rock", "alegre", "dance", "fiesta"]):
        bpm = 128
    elif any(k in sub_lower for k in ["lenta", "relajante", "triste", "lofi", "dormir", "chill"]):
        bpm = 85

    beat_len = 60.0 / bpm
    total_beats = int(duration / beat_len)

    # Progresión armónica C - G - Am - F (I - V - vi - IV) en Hz
    chords = [
        [261.63, 329.63, 392.00], # C mayor
        [196.00, 246.94, 293.66], # G mayor
        [220.00, 261.63, 329.63], # A menor
        [174.61, 220.00, 261.63], # F mayor
    ]
    bass_notes = [130.81, 98.00, 110.00, 87.31]
    lead_scale = [523.25, 587.33, 659.25, 783.99, 880.00, 1046.50]

    # 1. Pista de Acordes Armónicos (Pads/Piano suave)
    chord_len_beats = 4
    for chord_idx, chord_freqs in enumerate(chords):
        start_t = chord_idx * chord_len_beats * beat_len
        end_t = min(duration, (chord_idx + 1) * chord_len_beats * beat_len)
        if start_t >= duration:
            break
        s_idx = int(start_t * sr)
        e_idx = int(end_t * sr)
        seg_t = t[s_idx:e_idx] - start_t
        seg_dur = end_t - start_t
        env = np.maximum(0, np.sin(np.pi * (seg_t / seg_dur))) ** 0.5
        chord_wave = sum(np.sin(2 * np.pi * f * seg_t) for f in chord_freqs) / 3.0
        audio[s_idx:e_idx] += 0.28 * chord_wave * env

    # 2. Pista de Melodía Principal (Lead Arpegiado)
    for b in range(total_beats):
        b_start = b * beat_len
        b_end = min(duration, (b + 1) * beat_len)
        s_idx = int(b_start * sr)
        e_idx = int(b_end * sr)
        b_t = t[s_idx:e_idx] - b_start
        note_freq = lead_scale[(b * 2 + 1) % len(lead_scale)]
        note_env = np.exp(-4.0 * b_t / beat_len)
        note_wave = (np.sin(2 * np.pi * note_freq * b_t) + 0.3 * np.sin(4 * np.pi * note_freq * b_t)) * note_env
        audio[s_idx:e_idx] += 0.35 * note_wave

    # 3. Pista de Bajo Profundo (Sub-bass)
    for b in range(0, total_beats, 2):
        b_start = b * beat_len
        b_end = min(duration, (b + 2) * beat_len)
        s_idx = int(b_start * sr)
        e_idx = int(b_end * sr)
        b_t = t[s_idx:e_idx] - b_start
        bass_freq = bass_notes[(b // 4) % len(bass_notes)]
        b_env = np.exp(-1.5 * b_t / (2 * beat_len))
        bass_wave = (np.sin(2 * np.pi * bass_freq * b_t) + 0.25 * np.sin(4 * np.pi * bass_freq * b_t)) * b_env
        audio[s_idx:e_idx] += 0.38 * bass_wave

    # 4. Ritmo / Percusión sutil (Hi-hat y Kick suave)
    for b in range(total_beats):
        b_start = b * beat_len
        s_idx = int(b_start * sr)
        # Kick en tiempos pares
        if b % 2 == 0:
            k_len = min(int(0.18 * sr), len(t) - s_idx)
            k_t = t[s_idx:s_idx+k_len] - b_start
            kick_f = 140 * np.exp(-25.0 * k_t)
            kick_env = np.exp(-15.0 * k_t)
            kick = np.sin(2 * np.pi * kick_f * k_t) * kick_env
            audio[s_idx:s_idx+k_len] += 0.45 * kick
        # Hi-hat en cada tiempo
        hh_len = min(int(0.06 * sr), len(t) - s_idx)
        hh_t = t[s_idx:s_idx+hh_len] - b_start
        hh_noise = np.random.normal(0, 0.2, hh_len) * np.exp(-40.0 * hh_t)
        audio[s_idx:s_idx+hh_len] += 0.15 * hh_noise

    # Normalizar volumen general
    max_val = np.max(np.abs(audio)) + 1e-6
    audio = audio / max_val
    audio_i16 = (audio * 29000).astype(np.int16)

    out_path = os.path.join(AUDIOS_DIR, filename)
    with wave.open(out_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_i16.tobytes())

    return filename

def generate_ai_audio(subject: str, audio_type: str = "sound_effect"):
    """
    Genera o descarga el audio correspondiente (efecto de sonido o canción instrumental).
    Retorna (filename: str, title: str, audio_type: str, description: str).
    """
    clean_sub = subject.lower().strip()
    slug = re.sub(r'[^a-z0-9]', '_', clean_sub)[:24]
    h = hashlib.md5(subject.encode("utf-8")).hexdigest()[:8]

    if audio_type == "sound_effect":
        # Buscar en catálogo de efectos auténticos
        matched_catalog_key = None
        for k in SFX_CATALOG:
            if k in clean_sub:
                matched_catalog_key = k
                break

        if matched_catalog_key:
            entry = SFX_CATALOG[matched_catalog_key]
            out_fn = f"sfx_{matched_catalog_key}_{h}.{entry['type']}"
            out_path = os.path.join(AUDIOS_DIR, out_fn)
            if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
                try:
                    req = urllib.request.Request(entry["url"], headers={"User-Agent": "DocumentStudioAudio/1.0"})
                    with urllib.request.urlopen(req, timeout=8) as res:
                        with open(out_path, "wb") as f:
                            f.write(res.read())
                    return out_fn, entry["title"], "sound_effect", f"Efecto de sonido auténtico de {matched_catalog_key} listo para reproducir."
                except Exception as e:
                    print(f"[AUDIO] Error descargando audio de catálogo: {e}, usando síntesis procedimental")

        # Síntesis acústica procedimental de alta definición
        out_fn = f"sfx_{slug}_{h}.wav"
        synthesize_procedural_sound(subject, out_fn)
        title = f"Efecto Acústico: {subject.title()}"
        return out_fn, title, "sound_effect", f"Sonido de '{subject}' sintetizado en 44.1 kHz con modulación acústica."

    else:
        # Generación de Canción / Composición Armónica
        out_fn = f"song_{slug}_{h}.wav"
        synthesize_procedural_song(subject, out_fn)
        title = f"Composición Musical IA: {subject.title()}"
        return out_fn, title, "song", f"Canción instrumental generada con melodía armónica, acordes, bajo y ritmo para '{subject}'."

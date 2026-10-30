"""English and Turkish strings. English is the default; Turkish when the system language is Turkish or asked for."""

from __future__ import annotations

import locale
import os

STRINGS: dict[str, dict[str, str]] = {
    # the sentence
    "record": {"en": "Record", "tr": "Kaydet"},
    "episodes of": {"en": "episodes of", "tr": "bölüm, görev:"},
    "on my": {"en": "on my", "tr": "kol:"},
    "into": {"en": "into", "tr": "hedef:"},
    "task placeholder": {"en": "what the arm should do", "tr": "kol ne yapacak (İngilizce)"},
    "dataset placeholder": {"en": "dataset-name", "tr": "dataset-adi"},
    "namespace placeholder": {"en": "user", "tr": "kullanıcı"},
    "arm ready": {"en": "SO-101", "tr": "SO-101"},
    "arm setup": {"en": "SO-101 · set up", "tr": "SO-101 · kur"},
    # summary under the sentence
    "new dataset": {"en": "new dataset", "tr": "yeni dataset"},
    "adds to": {"en": "adds to {n} episodes", "tr": "{n} bölümün üstüne"},
    "each": {"en": "{s} s each", "tr": "{s} sn bölüm"},
    "reset": {"en": "{s} s reset", "tr": "{s} sn reset"},
    "private hub": {"en": "private on the Hub", "tr": "Hub'da gizli"},
    "public hub": {"en": "public on the Hub", "tr": "Hub'da açık"},
    "local only": {"en": "local only", "tr": "sadece yerel"},
    "rerun": {"en": "Rerun", "tr": "Rerun"},
    "on hub": {"en": "{repo} is on the Hub with {n} episodes and not in {root}: the push will replace it.",
               "tr": "{repo} Hub'da {n} bölümle var ama {root} içinde yok: push onu değiştirir."},
    # problems
    "need task": {"en": "Write the task: what the arm should do.", "tr": "Görevi yaz: kol ne yapacak."},
    "need dataset": {"en": "Name the dataset.", "tr": "Dataset'e bir ad ver."},
    "need login": {"en": "Log in to Hugging Face (ctrl+s) or turn off the push.",
                   "tr": "Hugging Face'e giriş yap (ctrl+s) ya da push'u kapat."},
    "need namespace": {"en": "Pick the Hugging Face user or org.", "tr": "Hugging Face kullanıcısını ya da org'u seç."},
    "need port": {"en": "Pick the {role} port (ctrl+s › Arms).", "tr": "{role} portunu seç (ctrl+s › Kollar)."},
    "port gone": {"en": "The {role} port {port} is not plugged in.", "tr": "{role} portu {port} takılı değil."},
    "same port": {"en": "Follower and leader are on the same port.", "tr": "Follower ve leader aynı portta."},
    "no calibration": {"en": "No calibration for the {role} at {path}. Calibrate it first (so101-cal).",
                       "tr": "{role} için kalibrasyon yok: {path}. Önce kalibre et (so101-cal)."},
    "same camera": {"en": "Two cameras use index {i}.", "tr": "İki kamera da {i} numaralı."},
    "broken dataset": {"en": "{root} exists but is not a LeRobot dataset. Rename or remove it.",
                       "tr": "{root} var ama LeRobot dataset'i değil. Adını değiştir ya da sil."},
    "fps mismatch": {"en": "{root} was recorded at {a} fps, now {b}.",
                     "tr": "{root} {a} fps ile kaydedilmiş, şimdi {b}."},
    "cams mismatch": {"en": "{root} has cameras {a}, now {b}.", "tr": "{root} kameraları {a}, şimdi {b}."},
    "confirm hub": {"en": "Record anyway? enter yes · esc no", "tr": "Yine de kaydedilsin mi? enter evet · esc hayır"},
    # home keys
    "k record": {"en": "record", "tr": "kaydet"},
    "k setup": {"en": "setup", "tr": "kurulum"},
    "k command": {"en": "command", "tr": "komut"},
    "k lang": {"en": "türkçe", "tr": "english"},
    "k quit": {"en": "quit", "tr": "çık"},
    "k close": {"en": "close", "tr": "kapat"},
    "k copy": {"en": "copy", "tr": "kopyala"},
    # recording
    "episode": {"en": "EPISODE {i} / {n}", "tr": "BÖLÜM {i} / {n}"},
    "ph starting": {"en": "Starting lerobot-record…", "tr": "lerobot-record başlıyor…"},
    "ph connecting": {"en": "Connecting the {device}…", "tr": "{device} bağlanıyor…"},
    "ph record": {"en": "● RECORDING", "tr": "● KAYIT"},
    "ph reset": {"en": "RESET · put everything back", "tr": "RESET · her şeyi yerine koy"},
    "ph saving": {"en": "Saving the episode…", "tr": "Bölüm kaydediliyor…"},
    "ph pushing": {"en": "Uploading to the Hub…", "tr": "Hub'a yükleniyor…"},
    "ph done": {"en": "Done.", "tr": "Bitti."},
    "ph stopped": {"en": "Stopped.", "tr": "Durduruldu."},
    "ph failed": {"en": "It stopped with an error.", "tr": "Hatayla durdu."},
    "saved n": {"en": "{n} episodes saved in {root}", "tr": "{n} bölüm kaydedildi: {root}"},
    "redone": {"en": "{n} re-recorded", "tr": "{n} tekrar"},
    "k next": {"en": "next", "tr": "sonraki"},
    "k redo": {"en": "redo", "tr": "tekrarla"},
    "k stop": {"en": "stop", "tr": "durdur"},
    "k abort": {"en": "abort", "tr": "iptal"},
    "k home": {"en": "back", "tr": "geri"},
    "k open": {"en": "open on the Hub", "tr": "Hub'da aç"},
    "k viewer": {"en": "visualize", "tr": "görselleştir"},
    "global yes": {"en": "→ ← esc work in the Rerun window too", "tr": "→ ← esc Rerun penceresinde de çalışır"},
    "global no": {"en": "keys only here (no macOS Accessibility permission for global keys)",
                  "tr": "tuşlar sadece burada (global tuşlar için macOS Erişilebilirlik izni yok)"},
    "aborting": {"en": "Stopping… (ctrl+c again kills it)", "tr": "Durduruluyor… (tekrar ctrl+c zorla kapatır)"},
    # setup
    "setup": {"en": "Setup", "tr": "Kurulum"},
    "tab hub": {"en": "Hugging Face", "tr": "Hugging Face"},
    "tab arms": {"en": "Arms", "tr": "Kollar"},
    "tab cameras": {"en": "Cameras", "tr": "Kameralar"},
    "tab options": {"en": "Options", "tr": "Ayarlar"},
    "hub as": {"en": "Logged in as {user}", "tr": "{user} olarak giriş yapıldı"},
    "hub orgs": {"en": "orgs: {orgs}", "tr": "org'lar: {orgs}"},
    "hub none": {"en": "Not logged in.", "tr": "Giriş yapılmadı."},
    "hub checking": {"en": "Checking the Hub…", "tr": "Hub kontrol ediliyor…"},
    "hub error": {"en": "The Hub did not accept the saved token: {e}", "tr": "Hub kayıtlı token'ı kabul etmedi: {e}"},
    "hub token help": {"en": "A token with write access: huggingface.co/settings/tokens. It is stored where "
                                "huggingface_hub keeps it (~/.cache/huggingface/token), so lerobot and the hf "
                                "CLI use it too.",
                       "tr": "Yazma yetkili bir token: huggingface.co/settings/tokens. huggingface_hub'ın "
                             "sakladığı yere kaydedilir (~/.cache/huggingface/token); lerobot ve hf CLI da "
                             "onu kullanır."},
    "token placeholder": {"en": "hf_…", "tr": "hf_…"},
    "save token": {"en": "Save token", "tr": "Token'ı kaydet"},
    "logout": {"en": "Log out", "tr": "Çıkış"},
    "follower port": {"en": "Follower port", "tr": "Follower portu"},
    "leader port": {"en": "Leader port", "tr": "Leader portu"},
    "id": {"en": "id", "tr": "id"},
    "calibration dir": {"en": "Calibration folder", "tr": "Kalibrasyon klasörü"},
    "calibration default": {"en": "(LeRobot's default)", "tr": "(LeRobot varsayılanı)"},
    "ports help": {"en": "Unplug one arm's USB: the port that disappears is that arm's.",
                   "tr": "Bir kolun USB'sini çek: kaybolan port o kolundur."},
    "port unplugged": {"en": "{port} was just unplugged", "tr": "{port} az önce çıkarıldı"},
    "port plugged": {"en": "{port} was just plugged in", "tr": "{port} az önce takıldı"},
    "no ports": {"en": "No USB boards found.", "tr": "USB kart bulunamadı."},
    "cal found": {"en": "✓ {role}: {path}", "tr": "✓ {role}: {path}"},
    "cal missing": {"en": "✗ {role}: no {path}", "tr": "✗ {role}: {path} yok"},
    "cam name": {"en": "name", "tr": "ad"},
    "cam index": {"en": "index", "tr": "numara"},
    "cam size": {"en": "Size (all cameras)", "tr": "Boyut (tüm kameralar)"},
    "swap": {"en": "Swap", "tr": "Değiştir"},
    "add camera": {"en": "Add", "tr": "Ekle"},
    "remove camera": {"en": "Remove last", "tr": "Sonuncuyu sil"},
    "scan": {"en": "Scan", "tr": "Tara"},
    "scanning": {"en": "Scanning cameras…", "tr": "Kameralar taranıyor…"},
    "scan found": {"en": "Cameras that answer: {found}", "tr": "Cevap veren kameralar: {found}"},
    "cam help": {"en": "Check each picture: top sees the table, wrist sees the gripper. An iPhone nearby can shift "
                       "the numbers.",
                 "tr": "Görüntülere bak: top masayı, wrist gripper'ı görmeli. Yakındaki bir iPhone numaraları "
                       "kaydırabilir."},
    "no picture": {"en": "no picture", "tr": "görüntü yok"},
    "episode s": {"en": "Episode (s)", "tr": "Bölüm (sn)"},
    "reset s": {"en": "Reset (s)", "tr": "Reset (sn)"},
    "fps": {"en": "FPS", "tr": "FPS"},
    "data dir": {"en": "Data folder", "tr": "Veri klasörü"},
    "opt push": {"en": "Push to the Hub at the end", "tr": "Sonunda Hub'a yükle"},
    "opt private": {"en": "Private on the Hub", "tr": "Hub'da gizli"},
    "opt display": {"en": "Open the Rerun viewer", "tr": "Rerun'ı aç"},
    "opt sounds": {"en": "Spoken cues", "tr": "Sesli uyarılar"},
    "opt streaming": {"en": "Encode video while recording", "tr": "Videoyu kayıt sırasında encode et"},
    "opt global": {"en": "Global keys (→ ← esc anywhere)", "tr": "Global tuşlar (→ ← esc her yerde)"},
}

_lang = "en"


def detect() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "")
        if v:
            return "tr" if v.lower().startswith("tr") else "en"
    try:
        loc = locale.getlocale()[0] or ""
    except ValueError:
        loc = ""
    return "tr" if loc.lower().startswith("tr") else "en"


def set_lang(lang: str) -> None:
    global _lang
    _lang = "tr" if lang == "tr" else "en"


def get_lang() -> str:
    return _lang


def t(key: str, **kw) -> str:
    entry = STRINGS.get(key)
    s = entry.get(_lang) or entry["en"] if entry else key
    return s.format(**kw) if kw else s

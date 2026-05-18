from __future__ import annotations

import re
from typing import Any, Iterable


REGULATION_REF = "Perpres 82/2018 Pasal 52 jo. Perpres 59/2024"


_RULES: tuple[dict[str, str], ...] = (
    {
        "pattern": "self_requested_referral",
        "category": "procedure_not_compliant",
        "severity": "high",
        "regex": r"\b(?:rujukan|masuk|rawat\s+inap)\b.{0,60}\b(?:permintaan\s+sendiri|tanpa\s+rujukan)\b|\btanpa\s+(?:surat\s+)?rujukan\b.{0,40}\b(?:fktp|bpjs|jkn)\b",
        "message": "Potensi tidak dijamin: pelayanan tidak sesuai prosedur/rujukan atas permintaan sendiri.",
        "recommendation": "Verifikasi alur rujukan, SEP, indikasi rawat inap, dan status gawat darurat sebelum submit klaim.",
    },
    {
        "pattern": "non_contract_facility_without_emergency",
        "category": "facility_not_contracted",
        "severity": "high",
        "regex": r"\b(?:faskes|rs|rumah\s+sakit)\b.{0,50}\b(?:tidak|non)\s+(?:bekerja\s*sama|kerja\s*sama|provider|rekanan)\b|\bnon\s+provider\b",
        "message": "Potensi tidak dijamin: pelayanan di faskes tidak bekerja sama, kecuali kondisi darurat.",
        "recommendation": "Pastikan bukti kegawatdaruratan, stabilisasi, dan rujukan ke faskes kerja sama tersedia.",
    },
    {
        "pattern": "work_accident_other_scheme",
        "category": "other_primary_payer",
        "severity": "high",
        "regex": r"\b(?:kecelakaan\s+kerja|penyakit\s+akibat\s+kerja|hubungan\s+kerja|jkk|bpjs\s+ketenagakerjaan)\b",
        "message": "Potensi penjamin pertama bukan JKN: kecelakaan kerja/penyakit akibat kerja.",
        "recommendation": "Koordinasikan dengan JKK/BPJS Ketenagakerjaan atau pemberi kerja sebelum klaim JKN.",
    },
    {
        "pattern": "traffic_accident_other_scheme",
        "category": "other_primary_payer",
        "severity": "high",
        "regex": r"\b(?:kecelakaan\s+lalu\s+lintas|laka\s+lantas|jasa\s+raharja|kll|cedera\s+akibat\s+tabrakan|tabrakan\s+(?:motor|mobil))\b",
        "message": "Potensi penjamin pertama bukan JKN: kecelakaan lalu lintas masuk koordinasi Jasa Raharja/program wajib.",
        "recommendation": "Verifikasi kronologi KLL, laporan kepolisian, plafon Jasa Raharja, dan koordinasi manfaat.",
    },
    {
        "pattern": "overseas_service",
        "category": "outside_jkn_scope",
        "severity": "high",
        "regex": r"\b(?:pelayanan|berobat|dirawat|operasi)\b.{0,40}\b(?:luar\s+negeri|singapura|malaysia|penang)\b",
        "message": "Potensi tidak dijamin: pelayanan kesehatan dilakukan di luar negeri.",
        "recommendation": "Pisahkan episode luar negeri dari klaim JKN domestik.",
    },
    {
        "pattern": "aesthetic_cosmetic",
        "category": "non_medical_purpose",
        "severity": "high",
        "regex": r"\b(?:estetik|estetika|kosmetik|kecantikan|blepharoplasty|rhinoplasty|filler|botox|operasi\s+plastik\s+kecantikan)\b",
        "message": "Potensi tidak dijamin: pelayanan untuk tujuan estetik/kosmetik.",
        "recommendation": "Pastikan ada indikasi medis rekonstruktif bila layanan tetap diajukan sebagai JKN.",
    },
    {
        "pattern": "infertility",
        "category": "non_covered_service",
        "severity": "high",
        "regex": r"\b(?:infertilitas|subfertilitas|bayi\s+tabung|ivf|inseminasi|program\s+hamil)\b",
        "message": "Potensi tidak dijamin: pelayanan untuk mengatasi infertilitas.",
        "recommendation": "Jangan ajukan sebagai manfaat JKN kecuali episode memiliki indikasi medis lain yang terpisah dan terdokumentasi.",
    },
    {
        "pattern": "orthodontic",
        "category": "non_covered_service",
        "severity": "medium",
        "regex": r"\b(?:ortodonsi|orthodonti|behel|meratakan\s+gigi|kawat\s+gigi)\b",
        "message": "Potensi tidak dijamin: pelayanan meratakan gigi/ortodonsi.",
        "recommendation": "Verifikasi apakah tindakan gigi bersifat kuratif atau ortodonsi estetik.",
    },
    {
        "pattern": "drug_or_alcohol_dependence",
        "category": "substance_related",
        "severity": "high",
        "regex": r"\b(?:ketergantungan|dependen|adiksi|intoksikasi)\b.{0,40}\b(?:obat|narkoba|napza|alkohol)\b|\b(?:alkoholisme|napza|narkoba)\b",
        "message": "Potensi tidak dijamin: gangguan kesehatan akibat ketergantungan obat dan/atau alkohol.",
        "recommendation": "Verifikasi diagnosis, penyebab episode, dan skema layanan rehabilitasi yang berlaku.",
    },
    {
        "pattern": "self_harm_or_dangerous_hobby",
        "category": "self_inflicted_or_high_risk",
        "severity": "high",
        "regex": r"\b(?:menyakiti\s+diri|self\s*harm|percobaan\s+bunuh\s+diri|tentamen\s+suicid|hobi\s+berbahaya|balap\s+liar)\b",
        "message": "Potensi tidak dijamin: cedera akibat sengaja menyakiti diri sendiri atau hobi berbahaya.",
        "recommendation": "Verifikasi kronologi klinis dan ketentuan penjaminan sebelum submit.",
    },
    {
        "pattern": "traditional_or_alternative_unproven",
        "category": "unproven_therapy",
        "severity": "medium",
        "regex": r"\b(?:komplementer|alternatif|tradisional|chiropractic|shin\s*she|terapi\s+bekam|akupunktur)\b",
        "message": "Potensi tidak dijamin: terapi komplementer/alternatif/tradisional yang belum dinyatakan efektif HTA.",
        "recommendation": "Pastikan terapi termasuk manfaat JKN dan memiliki indikasi medis yang diakui.",
    },
    {
        "pattern": "experimental_treatment",
        "category": "unproven_therapy",
        "severity": "high",
        "regex": r"\b(?:eksperimen|experimental|uji\s+coba|clinical\s+trial|percobaan\s+terapi)\b",
        "message": "Potensi tidak dijamin: pengobatan/tindakan medis percobaan atau eksperimen.",
        "recommendation": "Jangan masukkan biaya eksperimen ke klaim JKN rutin.",
    },
    {
        "pattern": "contraceptive_or_cosmetic_supply",
        "category": "non_covered_item",
        "severity": "medium",
        "regex": r"\b(?:alat\s+kontrasepsi|obat\s+kontrasepsi|kondom|iud|implan\s+kb|kosmetik)\b",
        "message": "Potensi tidak dijamin: alat/obat kontrasepsi atau kosmetik.",
        "recommendation": "Pisahkan item non-JKN dari komponen klaim INA-CBG bila tidak termasuk manfaat episode.",
    },
    {
        "pattern": "household_health_supply",
        "category": "non_covered_item",
        "severity": "medium",
        "regex": r"\b(?:perbekalan\s+kesehatan\s+rumah\s+tangga|popok|diapers|underpad|tisu\s+basah|sabun|shampoo|susu\s+formula)\b",
        "message": "Potensi tidak dijamin: perbekalan kesehatan rumah tangga.",
        "recommendation": "Pastikan item rumah tangga tidak ikut dibebankan sebagai manfaat JKN.",
    },
    {
        "pattern": "disaster_outbreak_other_scheme",
        "category": "other_public_funding",
        "severity": "medium",
        "regex": r"\b(?:bencana|tanggap\s+darurat|kejadian\s+luar\s+biasa|klb|wabah)\b",
        "message": "Potensi pendanaan lain: pelayanan akibat bencana/KLB/wabah pada masa tanggap darurat.",
        "recommendation": "Verifikasi skema pendanaan bencana/KLB sebelum klaim JKN.",
    },
    {
        "pattern": "preventable_adverse_event",
        "category": "preventable_adverse_event",
        "severity": "high",
        "regex": r"\b(?:kejadian\s+tidak\s+diharapkan|ktd|adverse\s+event|salah\s+obat|wrong\s+site|infeksi\s+nosokomial\s+dapat\s+dicegah)\b",
        "message": "Potensi tidak dijamin: pelayanan pada kejadian tidak diharapkan yang dapat dicegah.",
        "recommendation": "Review mutu klinis dan jangan submit sebelum klarifikasi RCA/komite mutu.",
    },
    {
        "pattern": "social_service",
        "category": "outside_jkn_scope",
        "severity": "medium",
        "regex": r"\b(?:bakti\s+sosial|baksos|pelayanan\s+sosial)\b",
        "message": "Potensi tidak dijamin: pelayanan diselenggarakan dalam rangka bakti sosial.",
        "recommendation": "Pisahkan episode bakti sosial dari klaim JKN rutin.",
    },
    {
        "pattern": "crime_victim_other_scheme",
        "category": "other_public_funding",
        "severity": "high",
        "regex": r"\b(?:penganiayaan|kekerasan\s+seksual|perdagangan\s+orang|tindak\s+pidana\s+perdagangan\s+orang|korban\s+terorisme|terorisme)\b",
        "message": "Potensi skema pendanaan lain: korban tindak pidana tertentu yang telah dijamin K/L atau Pemda.",
        "recommendation": "Verifikasi apakah pembiayaan dijamin skema K/L/Pemda sebelum klaim JKN.",
    },
    {
        "pattern": "defense_police_specific_service",
        "category": "other_public_funding",
        "severity": "medium",
        "regex": r"\b(?:kementerian\s+pertahanan|kemenhan|tni|polri|bhayangkara|asabri)\b",
        "message": "Potensi skema khusus: pelayanan tertentu terkait Kemenhan/TNI/Polri.",
        "recommendation": "Verifikasi status penjamin dan skema khusus sebelum submit JKN.",
    },
    {
        "pattern": "covered_by_other_program",
        "category": "other_primary_payer",
        "severity": "high",
        "regex": r"\b(?:ditanggung|dijamin|dicover)\b.{0,50}\b(?:program\s+lain|asuransi\s+lain|taspen|asabri|jasa\s+raharja|bpjs\s+ketenagakerjaan|pemda)\b",
        "message": "Potensi tidak dijamin JKN: pelayanan sudah ditanggung program lain.",
        "recommendation": "Tentukan penjamin utama dan dokumentasikan koordinasi manfaat.",
    },
)


def _iter_text(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if value is None:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _iter_text(child, child_path)
        return
    if isinstance(value, (list, tuple)):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            yield from _iter_text(child, child_path)
        return
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        if text:
            yield path or "resume", text


def _snippet(text: str, start: int, end: int) -> str:
    left = max(0, start - 48)
    right = min(len(text), end + 72)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    return prefix + re.sub(r"\s+", " ", text[left:right]).strip() + suffix


def build_jkn_non_covered_alerts(source: Any) -> list[dict[str, str]]:
    """Return conservative review flags for JKN non-covered benefit risks.

    These flags are not automatic claim rejection. They identify episodes that
    need payer/procedure review before JKN submission.
    """

    alerts: list[dict[str, str]] = []
    text_items = list(_iter_text(source))
    for rule in _RULES:
        pattern = re.compile(rule["regex"], re.IGNORECASE)
        for field, text in text_items:
            match = pattern.search(text)
            if not match:
                continue
            alerts.append(
                {
                    "type": "jkn_non_covered_risk",
                    "field": field,
                    "pattern": rule["pattern"],
                    "rule_id": f"JKN_NON_COVERED_{rule['pattern'].upper()}",
                    "category": rule["category"],
                    "message": rule["message"],
                    "recommendation": rule["recommendation"],
                    "snippet": _snippet(text, match.start(), match.end())[:180],
                    "severity": rule["severity"],
                    "regulation_ref": REGULATION_REF,
                }
            )
            break
    return alerts


def merge_jkn_non_covered_into_payload(payload: dict, source: Any) -> dict:
    if not isinstance(payload, dict):
        return payload

    alerts = build_jkn_non_covered_alerts(source)
    if not alerts:
        payload.setdefault("non_jaminan_flags", payload.get("non_jaminan_flags") or [])
        payload.setdefault("non_jaminan_status", "clear")
        return payload

    enriched = dict(payload)
    existing = [item for item in (enriched.get("non_jaminan_flags") or []) if isinstance(item, dict)]
    seen = {
        (
            str(item.get("pattern") or "").lower(),
            str(item.get("field") or "").lower(),
            str(item.get("message") or "").lower(),
        )
        for item in existing
    }
    for alert in alerts:
        key = (
            str(alert.get("pattern") or "").lower(),
            str(alert.get("field") or "").lower(),
            str(alert.get("message") or "").lower(),
        )
        if key not in seen:
            existing.append(alert)
            seen.add(key)

    quality = [item for item in (enriched.get("quality_issues") or []) if isinstance(item, dict)]
    quality_seen = {
        (
            str(item.get("pattern") or "").lower(),
            str(item.get("field") or "").lower(),
            str(item.get("message") or "").lower(),
        )
        for item in quality
    }
    for alert in existing:
        key = (
            str(alert.get("pattern") or "").lower(),
            str(alert.get("field") or "").lower(),
            str(alert.get("message") or "").lower(),
        )
        if key not in quality_seen:
            quality.append(dict(alert))
            quality_seen.add(key)

    enriched["non_jaminan_flags"] = existing
    enriched["non_jaminan_status"] = "review"
    enriched["quality_issues"] = quality
    if enriched.get("status") in ("complete", "already_scanned", "", None):
        enriched["status"] = "findings"
    return enriched

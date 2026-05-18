set -e
cd /opt/mediguard-pro || exit 1

curl -fsSL https://raw.githubusercontent.com/frezaade31-pixel/claim-auditor-ui/main/ops/mediguard-files/e0e411a/backend/modules/jkn_non_covered_filter.py -o backend/modules/jkn_non_covered_filter.py

python3 - <<'PY'
from pathlib import Path

main = Path('backend/main.py')
text = main.read_text(encoding='utf-8')
if 'merge_jkn_non_covered_into_payload(scan_result, resume_fields)' not in text:
    text = text.replace(
        '    from modules.resume_quality import build_resume_quality_issues\n',
        '    from modules.jkn_non_covered_filter import merge_jkn_non_covered_into_payload\n    from modules.resume_quality import build_resume_quality_issues\n',
        1,
    )
    text = text.replace(
        '    scan_result = await _attach_scan_resume_artifact(scan_result, original_input or noreg, rm)\n',
        '    scan_result = merge_jkn_non_covered_into_payload(scan_result, resume_fields)\n    scan_result = await _attach_scan_resume_artifact(scan_result, original_input or noreg, rm)\n',
        1,
    )
if 'payload = merge_jkn_non_covered_into_payload(payload, fields)' not in text:
    text = text.replace(
        '    from modules.resume_quality import (\n',
        '    from modules.jkn_non_covered_filter import merge_jkn_non_covered_into_payload\n    from modules.resume_quality import (\n',
        1,
    )
    text = text.replace(
        '    payload["quality_issues"] = merge_quality_issues(payload.get("quality_issues"), inferred)\n',
        '    payload["quality_issues"] = merge_quality_issues(payload.get("quality_issues"), inferred)\n    payload = merge_jkn_non_covered_into_payload(payload, fields)\n',
        1,
    )
main.write_text(text, encoding='utf-8')

resume = Path('backend/modules/resume_quality.py')
text = resume.read_text(encoding='utf-8')
if 'MEDIGUARD_E0E411A_HD_CDL_RULE' not in text:
    text += r'''

# MEDIGUARD_E0E411A_HD_CDL_RULE
import re as _mg_hd_re

_MG_ORIGINAL_BUILD_RESUME_QUALITY_ISSUES = build_resume_quality_issues


def _mg_hd_iter_text(value):
    if value is None:
        return
    if isinstance(value, dict):
        for child in value.values():
            yield from _mg_hd_iter_text(child)
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            yield from _mg_hd_iter_text(child)
        return
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        if text:
            yield text


def _mg_hd_text(source):
    return " ".join(_mg_hd_iter_text(source) or []).lower()


def _mg_hd_has(text, *patterns):
    return any(_mg_hd_re.search(pattern, text, _mg_hd_re.IGNORECASE) for pattern in patterns)


def _mg_build_hd_cdl_malfunction_issues(source):
    text = _mg_hd_text(source)
    if not text:
        return []
    has_ckd = _mg_hd_has(text, r"\b(ckd|pgk|ggk|gagal\s+ginjal\s+kronik|penyakit\s+ginjal\s+kronik|esrd|end\s+stage\s+renal)\b")
    has_hd = _mg_hd_has(text, r"\b(hd|hemodialisis|hemodialisa|cuci\s+darah)\b")
    has_cdl_problem = _mg_hd_has(
        text,
        r"\b(cdl|double\s+lumen|kateter\s+(hd|dialisis)|akses\s+vaskular)\b.{0,80}\b(macet|malfungsi|malfunction|tidak\s+lancar|tersumbat|buntu|clot|beku|flow\s+buruk|low\s+flow|poor\s+flow|alarm|aspirasi\s+sulit|tekanan\s+arteri|tekanan\s+vena|reposisi|ganti)\b",
        r"\b(macet|malfungsi|malfunction|tidak\s+lancar|tersumbat|buntu|clot|beku|flow\s+buruk|low\s+flow|poor\s+flow|alarm|aspirasi\s+sulit|tekanan\s+arteri|tekanan\s+vena|reposisi|ganti)\b.{0,80}\b(cdl|double\s+lumen|kateter\s+(hd|dialisis)|akses\s+vaskular)\b",
    )
    if not (has_ckd and has_hd and has_cdl_problem):
        return []
    required = {
        'jadwal/HD terakhir': (
            r"\b(hd|hemodialisis|cuci\s+darah)\s+(terakhir|sebelumnya|jadwal)\b",
            r"\b(terakhir|sebelumnya|jadwal)\s+(hd|hemodialisis|cuci\s+darah)\b",
            r"\b(senin|selasa|rabu|kamis|jumat|sabtu|minggu)\b.{0,30}\b(hd|hemodialisis|cuci\s+darah)\b",
            r"\b\d+\s*x\s*(/|per)?\s*(minggu|mgg)\b",
        ),
        'lokasi/jenis akses': (
            r"\b(cdl|double\s+lumen|kateter\s+hd)\s+(jugular|jugularis|subclavia|femoral|kanan|kiri|tunnel|tempore)\b",
            r"\b(jugular|jugularis|subclavia|femoral|kanan|kiri|tunnel|tempore)\b.{0,40}\b(cdl|double\s+lumen|kateter\s+hd)\b",
        ),
        'bukti malfunction': (
            r"\b(qb|blood\s+flow)\b.{0,20}\b(<|kurang|hanya|rendah|turun)\b.{0,20}\b\d+",
            r"\b(alarm|tekanan\s+arteri|tekanan\s+vena|aspirasi\s+(lumen\s+)?sulit|tidak\s+bisa\s+aspirasi|flow\s+buruk|low\s+flow|hd\s+tidak\s+selesai|clot|beku|trombus|fibrin|tersumbat|buntu|macet)\b",
        ),
        'rencana/indikasi tindakan akses': (
            r"\b(evaluasi|reposisi|ganti|penggantian|pasang|pemasangan|aff|lepas|thrombolytic|urokinase|alteplase)\b.{0,60}\b(cdl|double\s+lumen|kateter|akses)\b",
            r"\b(cdl|double\s+lumen|kateter|akses)\b.{0,60}\b(evaluasi|reposisi|ganti|penggantian|pasang|pemasangan|aff|lepas)\b",
        ),
    }
    missing = [label for label, patterns in required.items() if not _mg_hd_has(text, *patterns)]
    if not missing:
        return []
    return [{
        'type': 'clinical_documentation_gap',
        'field': 'resume',
        'pattern': 'hd_cdl_malfunction_anamnesis_incomplete',
        'message': 'CKD on HD dengan CDL malfunction terdeteksi; lengkapi anamnesis klaim: ' + ', '.join(missing) + '.',
        'snippet': _mg_hd_re.sub(r"\s+", " ", text[:180]).strip(),
        'severity': 'high',
        'regulation_ref': 'JKN menjamin sesuai indikasi medis/prosedur; PERNEFRI akses vaskular HD; KDOQI CVC dysfunction.',
    }]


def build_resume_quality_issues(source):
    issues = list(_MG_ORIGINAL_BUILD_RESUME_QUALITY_ISSUES(source) or [])
    seen = {str(item.get('pattern') or '') for item in issues if isinstance(item, dict)}
    for item in _mg_build_hd_cdl_malfunction_issues(source):
        if item['pattern'] not in seen:
            issues.append(item)
            seen.add(item['pattern'])
    return issues
'''
resume.write_text(text, encoding='utf-8')

batch = Path('backend/modules/batch_scan_runner.py')
text = batch.read_text(encoding='utf-8')
if 'MEDIGUARD_E0E411A_BATCH_SCAN_JKN_WRAPPER' not in text:
    text += r'''

# MEDIGUARD_E0E411A_BATCH_SCAN_JKN_WRAPPER
_MG_ORIGINAL_APPLY_CLINICAL_RADAR_TO_RESULT = _apply_clinical_radar_to_result


def _mg_merge_quality(existing, additions):
    try:
        from modules.resume_quality import merge_quality_issues
        return merge_quality_issues(existing, additions)
    except Exception:
        merged = [item for item in (existing or []) if isinstance(item, dict)]
        seen = {str(item.get('pattern') or '') for item in merged}
        for item in additions or []:
            if isinstance(item, dict) and str(item.get('pattern') or '') not in seen:
                merged.append(item)
                seen.add(str(item.get('pattern') or ''))
        return merged


def _mg_enrich_batch_payload(payload, source_fields):
    from modules.jkn_non_covered_filter import merge_jkn_non_covered_into_payload
    from modules.resume_quality import build_resume_quality_issues
    if not isinstance(payload, dict):
        return payload
    source_fields = source_fields or payload.get('resume_fields') or payload
    quality = build_resume_quality_issues(source_fields) if source_fields else []
    payload = dict(payload)
    payload['quality_issues'] = _mg_merge_quality(payload.get('quality_issues'), quality)
    payload = merge_jkn_non_covered_into_payload(payload, source_fields)
    if payload.get('quality_issues') and payload.get('status') in ('complete', 'already_scanned', '', None):
        payload['status'] = 'findings'
    return payload


def _apply_clinical_radar_to_result(result, resume_fields=None, enrichment=None, existing_codes=None):
    payload = _MG_ORIGINAL_APPLY_CLINICAL_RADAR_TO_RESULT(result, resume_fields, enrichment, existing_codes)
    try:
        from modules.tarif_estimator import ensure_tarif_estimate
        payload = _mg_enrich_batch_payload(payload, resume_fields or (result or {}).get('resume_fields') or {})
        return ensure_tarif_estimate(payload, resume_fields or (result or {}).get('resume_fields') or {})
    except Exception:
        return payload


_MG_ORIGINAL_SCAN_WITH_RADAR = _scan_with_radar
async def _scan_with_radar(item, simrs_proxy_url):
    payload = await _MG_ORIGINAL_SCAN_WITH_RADAR(item, simrs_proxy_url)
    return _mg_enrich_batch_payload(payload, item.get('resume_fields') or item.get('resume') or item)


_MG_ORIGINAL_SCAN_WITH_CLAUDE = _scan_with_claude
async def _scan_with_claude(item, simrs_proxy_url):
    payload = await _MG_ORIGINAL_SCAN_WITH_CLAUDE(item, simrs_proxy_url)
    return _mg_enrich_batch_payload(payload, item.get('resume_fields') or item.get('resume') or item)
'''
batch.write_text(text, encoding='utf-8')
PY

python3 -m py_compile backend/main.py backend/modules/batch_scan_runner.py backend/modules/resume_quality.py backend/modules/jkn_non_covered_filter.py
docker compose up -d --build api
docker compose ps api
docker compose exec -T api python - <<'PY'
from modules.jkn_non_covered_filter import build_jkn_non_covered_alerts
from modules.resume_quality import build_resume_quality_issues
print('jkn_filter_ok', build_jkn_non_covered_alerts({'diagnosa_utama':'kecelakaan lalu lintas Jasa Raharja'})[0]['pattern'])
print('hd_cdl_rule_ok', build_resume_quality_issues({'diagnosa_utama':'CKD on HD','keluhan_utama':'CDL malfunction','lain_lain':'kontrol HD rutin'})[-1].get('pattern'))
PY
sleep 2
curl -sS http://127.0.0.1:8080/api/v1/health

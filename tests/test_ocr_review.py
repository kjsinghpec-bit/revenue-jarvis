import hashlib

from fastapi.testclient import TestClient

from revenue_jarvis import db, server
from revenue_jarvis.answer import Jarvis
from revenue_jarvis.retrieve import Retriever


def test_extraction_success_is_not_scan_verification(kb):
    settings, con = kb
    evidence = Retriever(con, settings.embed_model).search('partition')
    book = next(e for e in evidence if e.source_type == 'book')
    assert book.ocr_status == 'extracted'
    assert not book.scan_verified
    answer = Jarvis(settings, con).ask('partition').to_dict()
    assert any('OCR' in w and 'unverified' in w.lower() for w in answer['warnings'])
    assert all(not e['scan_verified'] for e in answer['evidence'] if e['source_type'] == 'book')


def test_review_expires_when_text_changes(kb):
    from revenue_jarvis import ocr_review
    _, con = kb
    con.execute("UPDATE pages SET image_sha256='scan-hash' WHERE pdf_page=167")
    doc_id, text = con.execute('SELECT doc_id,text_clean FROM pages WHERE pdf_page=167').fetchone()
    sha = hashlib.sha256(text.encode()).hexdigest()
    ocr_review.record_review(con, doc_id, 167, 'scan_verified', 'human reviewer', sha, 'scan-hash')
    assert ocr_review.page_review(con, doc_id, 167)['scan_verified']
    con.execute("UPDATE pages SET text_clean=text_clean || ' correction' WHERE pdf_page=167")
    assert not ocr_review.page_review(con, doc_id, 167)['scan_verified']
    assert ocr_review.page_review(con, doc_id, 167)['ocr_status'] == 'needs_review'


def test_review_expires_when_scan_changes(kb):
    from revenue_jarvis import ocr_review
    _, con = kb
    con.execute("UPDATE pages SET image_sha256='scan-hash' WHERE pdf_page=167")
    doc_id, text = con.execute('SELECT doc_id,text_clean FROM pages WHERE pdf_page=167').fetchone()
    ocr_review.record_review(con, doc_id, 167, 'scan_verified', 'human reviewer', hashlib.sha256(text.encode()).hexdigest(), 'scan-hash')
    con.execute("UPDATE pages SET image_sha256='different-scan' WHERE pdf_page=167")
    assert not ocr_review.page_review(con, doc_id, 167)['scan_verified']


def test_page_api_exposes_review_status_and_never_claims_quality_ok_is_verified(kb):
    settings, con = kb
    con.close()
    response = TestClient(server.create_app(settings)).get('/api/page/167/text').json()
    assert response['quality'] == 'ok'
    assert response['ocr_status'] == 'extracted'
    assert response['scan_verified'] is False


def test_import_check_rejects_missing_vector_and_stale_tokens(kb):
    from revenue_jarvis import ocr_review
    _, con = kb
    con.execute("DELETE FROM embeddings WHERE chunk_id='b167'")
    con.execute("UPDATE bm25_tokens SET tokens='[\"wrong\"]' WHERE chunk_id='b119'")
    report = ocr_review.check_import(con)
    assert not report['passed']
    assert any('b167' in e and 'vector' in e for e in report['errors'])
    assert any('b119' in e and 'tokens' in e for e in report['errors'])


def test_import_check_rejects_chunk_not_in_page(kb):
    from revenue_jarvis import ocr_review
    _, con = kb
    con.execute("UPDATE chunks SET text='old uncorrected text' WHERE id='b167'")
    report = ocr_review.check_import(con)
    assert not report['passed']
    assert any('b167' in e and 'page text' in e for e in report['errors'])


def test_import_check_valid_index_does_not_certify_ocr_accuracy(kb):
    from revenue_jarvis import ocr_review
    _, con = kb
    # Match the real indexer's law-title prefixes; the retrieval fixture omits them.
    import json
    from revenue_jarvis.text import tokenize
    for r in con.execute("SELECT c.id,c.text,d.short_name FROM chunks c JOIN documents d ON d.id=c.doc_id WHERE c.source_type='law'").fetchall():
        con.execute('UPDATE bm25_tokens SET tokens=? WHERE chunk_id=?', (json.dumps(tokenize(r['short_name'] + ': ' + r['text'])), r['id']))
    report = ocr_review.check_import(con)
    assert report['passed'], report
    assert report['unverified_book_pages'] == 3
    assert report['scan_verified_book_pages'] == 0


def test_page_image_uses_matching_original_pdf(kb):
    from pathlib import Path
    settings, con = kb
    original = Path(__file__).resolve().parents[1] / 'Punjabi book .pdf'
    settings.book_pdf = original
    con.execute("UPDATE documents SET sha256='2bba1b70125a07d04efbc5c9f0dc06ad0059367e929fc2ffa9555c2a95e72980' WHERE kind='book'")
    con.commit()
    con.close()
    client = TestClient(server.create_app(settings))
    image = client.get('/api/page/167.png')
    assert image.status_code == 200
    assert image.content.startswith(b'\x89PNG\r\n\x1a\n')
    assert client.get('/api/page/999.png').status_code == 404


def test_wrong_pdf_cannot_be_displayed_as_citation_scan(kb, tmp_path):
    settings, con = kb
    wrong = tmp_path / 'wrong.pdf'
    wrong.write_bytes(b'wrong document')
    settings.book_pdf = wrong
    con.execute("UPDATE documents SET sha256='expected-original-hash' WHERE kind='book'")
    con.commit()
    con.close()
    assert TestClient(server.create_app(settings)).get('/api/page/167.png').status_code == 404


def test_stale_chunk_cannot_inherit_new_page_scan_verification(kb):
    from revenue_jarvis import ocr_review
    settings, con = kb
    con.execute("UPDATE pages SET image_sha256='scan-hash',text_clean='Corrected and verified page text.' WHERE pdf_page=167")
    doc_id = con.execute('SELECT doc_id FROM pages WHERE pdf_page=167').fetchone()[0]
    ocr_review.record_review(con, doc_id, 167, 'scan_verified', 'reviewer', hashlib.sha256(b'Corrected and verified page text.').hexdigest(), 'scan-hash')
    evidence = Retriever(con, settings.embed_model).search('partition')
    stale = next(e for e in evidence if e.pdf_page == 167)
    assert not stale.scan_verified
    assert stale.ocr_status == 'needs_review'


def test_import_gate_rejects_reused_embedding_after_text_correction(kb, tmp_path):
    from revenue_jarvis import ocr_review
    _, con = kb
    baseline = db.connect(tmp_path / 'baseline.db')
    con.backup(baseline)
    con.execute("UPDATE chunks SET text=text || ' correction' WHERE id='b167'")
    errors = ocr_review.check_import(con, baseline=baseline)['errors']
    assert any('b167' in e and 'baseline vector' in e for e in errors)
    baseline.close()


def test_review_cannot_be_recorded_without_matching_source_hashes(kb):
    import pytest
    from revenue_jarvis import ocr_review
    _, con = kb
    doc_id = con.execute('SELECT doc_id FROM pages WHERE pdf_page=167').fetchone()[0]
    with pytest.raises(ValueError, match='hashes'):
        ocr_review.record_review(con, doc_id, 167, 'scan_verified', 'reviewer', 'wrong', '')


def test_expected_corrected_page_hash_must_match_import(kb):
    from revenue_jarvis import ocr_review
    _, con = kb
    doc_id = con.execute('SELECT doc_id FROM pages WHERE pdf_page=167').fetchone()[0]
    report = ocr_review.check_import(con, [{'doc_id':doc_id, 'pdf_page':167, 'text_sha256':'wrong'}])
    assert not report['passed']
    assert any('corrected page text hash mismatch' in e for e in report['errors'])


def test_reingestion_can_remove_page_without_leaving_review_certificate(kb):
    from revenue_jarvis import ocr_review
    _, con = kb
    con.execute("UPDATE pages SET image_sha256='scan-hash' WHERE pdf_page=167")
    doc_id,text = con.execute('SELECT doc_id,text_clean FROM pages WHERE pdf_page=167').fetchone()
    ocr_review.record_review(con, doc_id, 167, 'scan_verified', 'reviewer', hashlib.sha256(text.encode()).hexdigest(), 'scan-hash')
    con.execute('DELETE FROM pages WHERE doc_id=? AND pdf_page=167',(doc_id,))
    assert con.execute('SELECT count(*) FROM page_reviews').fetchone()[0] == 0


def test_import_gate_rejects_partial_book_even_if_remaining_index_is_consistent(kb, tmp_path):
    from revenue_jarvis import ocr_review
    _,con=kb
    baseline=db.connect(tmp_path/'complete.db');con.backup(baseline)
    con.execute("DELETE FROM embeddings WHERE chunk_id='b167'")
    con.execute("DELETE FROM bm25_tokens WHERE chunk_id='b167'")
    con.execute("DELETE FROM chunks WHERE id='b167'")
    con.execute('DELETE FROM pages WHERE pdf_page=167')
    report=ocr_review.check_import(con,baseline=baseline)
    assert any('baseline book page' in e for e in report['errors'])
    baseline.close()


def test_ocr_import_cannot_change_existing_law_corpus(kb,tmp_path):
    from revenue_jarvis import ocr_review
    _,con=kb
    baseline=db.connect(tmp_path/'complete.db');con.backup(baseline)
    con.execute("UPDATE documents SET title='Changed legal source' WHERE kind='law'")
    report=ocr_review.check_import(con,baseline=baseline)
    assert any('law corpus changed' in e for e in report['errors'])
    baseline.close()

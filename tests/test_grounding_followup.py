import pytest
from revenue_jarvis.answer import validate, ModelAnswer, _spoken
from revenue_jarvis.retrieve import Evidence
from test_grounding import ev, reply


@pytest.mark.parametrize('quote', [
    'The fee is ₹100 and the fine is ₹500.',
    'ਫ਼ੀਸ ੧੦੦ ਰੁਪਏ ਅਤੇ ਜੁਰਮਾਨਾ ੫੦੦ ਰੁਪਏ ਹੈ।',
])
def test_fine_cannot_become_fee_within_one_sentence(quote):
    with pytest.raises(ValueError, match='numeric|context'):
        validate(reply('The fee is ₹500.', quote), [ev(text=quote)])


def test_bare_fee_cannot_borrow_section_number():
    source = ev('L1', 'The fee is prescribed separately.', section='111', provision_kind='section')
    with pytest.raises(ValueError, match='numeric|amount'):
        validate({'status':'answered','law_support':[{'text':'The fee is 111.','source_ids':['L1'],
                 'support':[{'source_id':'L1','quote':source.text}]}]}, [source])


def test_officer_cannot_borrow_other_officers_action():
    quote = 'The Collector may approve mutations. The Tehsildar may partition land.'
    with pytest.raises(ValueError, match='role|authority'):
        validate(reply('The Collector may partition land.',quote), [ev(text=quote)])


def test_action_scoped_negation_does_not_reject_unrelated_positive_claim():
    quote = 'The Collector may approve mutations. The Tehsildar cannot partition land.'
    a,_ = validate(reply('The Collector may approve mutations.',quote), [ev(text=quote)])
    assert a.claims


def test_book_and_law_disagreement_is_flagged_without_model_conflict_field():
    book = ev(text='The Collector may approve the application.')
    law = ev('L1',text='The Collector cannot approve the application.')
    raw={'status':'answered','claims':[{'text':book.text,'source_ids':['B1']}],
         'law_support':[{'text':law.text,'source_ids':['L1']}]}
    a,warnings=validate(raw,[book,law])
    assert a.status == 'insufficient'
    assert any('conflict' in w.lower() for w in warnings)
    assert 'approve' not in _spoken(a,'sir','en')


def test_english_claim_cannot_import_number_from_unrelated_punjabi_quote():
    b=ev(text='The fee is ₹100.')
    l=ev('L1',text='ਜੁਰਮਾਨਾ ੫੦੦ ਰੁਪਏ ਹੈ।')
    with pytest.raises(ValueError,match='numeric|context'):
        validate({'status':'answered','claims':[{'text':'The fee is ₹500.','source_ids':['B1','L1'],
        'support':[{'source_id':'B1','quote':b.text},{'source_id':'L1','quote':l.text}]}]},[b,l])


def test_correct_same_sentence_fee_still_passes():
    q='The fee is ₹100 and the fine is ₹500.'
    assert validate(reply('The fee is ₹100.',q),[ev(text=q)])[0].claims


@pytest.mark.parametrize('text', ['ਸ਼ੁਲਕ 100 रुपये ਹੈ।','ਸ਼ੁਲਕ ۱۰۰ روپے ਹੈ۔'])
def test_mixed_script_claims_are_rejected(text):
    with pytest.raises(ValueError,match='script'):
        validate(reply(text,'The fee is ₹100.'),[ev(text='The fee is ₹100.')])


def test_appeal_deadline_cannot_borrow_revision_deadline():
    q='An appeal must be filed within 30 days. A revision must be filed within 90 days.'
    with pytest.raises(ValueError,match='numeric|deadline'):
        validate(reply('An appeal must be filed within 90 days.',q),[ev(text=q)])


def test_assistant_collector_cannot_borrow_collectors_power():
    q='The Collector may approve the application.'
    with pytest.raises(ValueError,match='role|authority'):
        validate(reply('The Assistant Collector may approve the application.',q),[ev(text=q)])


def test_conflicting_fees_are_flagged_without_model_conflict_note():
    b=ev(text='The application fee is ₹100.')
    l=ev('L1',text='The application fee is ₹500.')
    a,w=validate({'status':'answered','claims':[{'text':b.text,'source_ids':['B1']}],
                 'law_support':[{'text':l.text,'source_ids':['L1']}]},[b,l])
    assert a.status == 'insufficient'
    assert any('conflict' in x.lower() for x in w)


def test_fees_for_different_proceedings_are_not_flagged_as_conflicting():
    b=ev(text='The partition application fee is ₹100.')
    l=ev('L1',text='The mutation application fee is ₹500.')
    a,w=validate({'status':'answered','claims':[{'text':b.text,'source_ids':['B1']}],
                 'law_support':[{'text':l.text,'source_ids':['L1']}]},[b,l])
    assert a.status == 'answered'
    assert not any('conflict' in x.lower() for x in w)


def test_two_fee_components_in_one_claim_are_not_self_contradiction():
    q='The application fee is ₹100 and the additional fee is ₹500.'
    a,_=validate(reply(q,q),[ev(text=q)])
    assert a.status == 'answered'


def test_shall_cannot_turn_permission_into_obligation():
    q='The Collector may approve the application.'
    with pytest.raises(ValueError,match='permission|requirement'):
        validate(reply('The Collector shall approve the application.',q),[ev(text=q)])


def test_gurmukhi_pipeline_reply_preserves_language_and_source_quote(kb):
    from test_answer import FakeBackend
    from revenue_jarvis.answer import Jarvis
    from revenue_jarvis.grounding import FORBIDDEN_SCRIPT
    settings,con=kb
    question='ਤਕਸੀਮ ਲਈ ਕੌਣ ਅਰਜ਼ੀ ਦੇ ਸਕਦਾ ਹੈ?'
    jarvis=Jarvis(settings,con,backend=None)
    source=next(e for e in jarvis.retriever.search(question) if e.short_name=='PLRA 1887')
    backend=FakeBackend({'status':'answered','law_support':[{
        'text':'ਕੋਈ ਵੀ ਸਾਂਝਾ ਮਾਲਕ ਆਪਣੇ ਹਿੱਸੇ ਦੀ ਤਕਸੀਮ ਲਈ ਮਾਲ ਅਫ਼ਸਰ ਕੋਲ ਅਰਜ਼ੀ ਦੇ ਸਕਦਾ ਹੈ।',
        'source_ids':[source.sid], 'support':[{'source_id':source.sid,'quote':source.text}]}]})
    answer=Jarvis(settings,con,backend).ask(question,log=False)
    assert answer.language=='pa' and answer.status=='answered'
    assert 'ਤਕਸੀਮ' in answer.spoken and not FORBIDDEN_SCRIPT.search(answer.spoken)
    assert answer.law_support[0]['support'][0]['quote']==source.text


def test_conflicting_support_quotes_cannot_be_pooled_to_justify_single_fee():
    b=ev(text='The application fee is ₹100.')
    l=ev('L1',text='The application fee is ₹500.')
    with pytest.raises(ValueError,match='conflict'):
        validate({'status':'answered','claims':[{'text':'The application fee is ₹500.','source_ids':['B1','L1'],
        'support':[{'source_id':'B1','quote':b.text},{'source_id':'L1','quote':l.text}]}]},[b,l])

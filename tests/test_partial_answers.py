import json
from pathlib import Path

from revenue_jarvis.answer import validate
from revenue_jarvis.retrieve import Evidence
from test_grounding import ev


def test_partial_mode_keeps_supported_claim_and_drops_invented_fee():
    source=ev(text='The application fee is ₹100.')
    raw={'status':'answered','claims':[
        {'text':source.text,'source_ids':['B1']},
        {'text':'The application fee is ₹500.','source_ids':['B1'],'support':[{'source_id':'B1','quote':source.text}]}]}
    a,w=validate(raw,[source],allow_partial=True)
    assert a.status=='answered' and a.partial_answer
    assert [c.text for c in a.claims]==[source.text]
    assert any('partial' in s.lower() for s in w)


def test_partial_mode_does_not_rescue_fabricated_quote():
    source=ev(text='The application fee is ₹100.')
    a,_=validate({'status':'answered','claims':[{'text':'The fee is ₹500.','source_ids':['B1'],
                 'support':[{'source_id':'B1','quote':'The fee is ₹500.'}]}]},[source],allow_partial=True)
    assert a.status=='insufficient' and not a.claims


def test_original_live_responses_have_supported_answer_content():
    fixture=Path(__file__).parent/'fixtures/withheld_live_answers.json'
    for record in json.loads(fixture.read_text())['cases']:
        case=record['case']
        raw=record['raw']
        evidence=[Evidence(**{k:v for k,v in e.items() if k in Evidence.__dataclass_fields__}) for e in record['evidence']]
        a,_=validate(raw,evidence,allow_partial=True)
        assert a.status=='answered' and a.partial_answer
        assert a.claims or a.law_support
        if case=='5':
            assert 'District Revenue Officers' in a.claims[0].text
            assert not any('1st Grade' in c.text for c in a.claims)
        else:
            assert any('150' in c.text for c in a.claims+a.law_support)

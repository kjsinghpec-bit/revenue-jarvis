import pytest
from revenue_jarvis.answer import validate
from revenue_jarvis.grounding import numeric_facts
from revenue_jarvis.retrieve import Evidence


def book(text):
    return Evidence('B1','book','book',text,'Bhumbak','Bhumbak',pdf_page=183,printed_page='168')


def answer(text,quote):
    return {'status':'answered','claims':[{'text':text,'source_ids':['B1'],
            'support':[{'source_id':'B1','quote':quote}]}]}


def test_book_can_describe_section_stated_in_its_cited_text():
    q='ਧਾਰਾ 150 ਤਹਿਤ ਮਾਲ ਅਫ਼ਸਰ ਨੂੰ ਨਾਜਾਇਜ਼ ਕਬਜ਼ੇ ਨੂੰ ਖਾਲੀ ਕਰਵਾਉਣ ਲਈ ਦਰਖਾਸਤ ਦੇ ਸਕਦਾ ਹੈ।'
    a,_=validate(answer('An application to remove encroachment may be made under section 150.',q),[book(q)])
    assert a.status=='answered'


def test_book_locator_stated_in_excerpt_is_not_lost_when_quote_covers_substantive_part():
    text='ਧਾਰਾ 150 ਤਹਿਤ ਦਰਖਾਸਤ। ਮਾਲ ਅਫ਼ਸਰ ਨੂੰ ਨਾਜਾਇਜ਼ ਕਬਜ਼ੇ ਨੂੰ ਖਾਲੀ ਕਰਵਾਉਣ ਲਈ ਦਰਖਾਸਤ ਦੇ ਸਕਦਾ ਹੈ।'
    quote='ਮਾਲ ਅਫ਼ਸਰ ਨੂੰ ਨਾਜਾਇਜ਼ ਕਬਜ਼ੇ ਨੂੰ ਖਾਲੀ ਕਰਵਾਉਣ ਲਈ ਦਰਖਾਸਤ ਦੇ ਸਕਦਾ ਹੈ।'
    a,_=validate(answer('ਧਾਰਾ 150 ਤਹਿਤ ਮਾਲ ਅਫ਼ਸਰ ਨੂੰ ਦਰਖਾਸਤ ਦੇ ਸਕਦਾ ਹੈ।',quote),[book(text)])
    assert a.status=='answered'


def test_locator_cannot_be_reused_as_a_count():
    source=Evidence('L1','law','law','Applications may be made by joint owners.','Act','Act',section='150',provision_kind='section')
    with pytest.raises(ValueError,match='numeric'):
        validate({'status':'answered','law_support':[{'text':'150 applications may be made by joint owners.','source_ids':['L1'],
                 'support':[{'source_id':'L1','quote':source.text}]}]},[source])


def test_wrong_book_section_still_rejected():
    q='ਧਾਰਾ 150 ਤਹਿਤ ਦਰਖਾਸਤ ਦੇ ਸਕਦਾ ਹੈ।'
    with pytest.raises(ValueError,match='section|locator'):
        validate(answer('An application may be made under section 151.',q),[book(q)])


def test_known_numeric_values_are_plain_decimal_not_exponents():
    assert ('number','150') in numeric_facts('150')
    assert ('currency','100') in numeric_facts('₹100')


def test_nri_partition_case_description_does_not_treat_noun_as_officer_action():
    q='ਪੰਜਾਬ ਵਿੱਚ ਤਕਸੀਮ ਦੇ ਜਿਹੜੇ ਕੇਸਾਂ ਵਿੱਚ ਪਟੀਸ਼ਨਰ ਪ੍ਰਵਾਸੀ ਭਾਰਤੀ ਹਨ ਉਨ੍ਹਾਂ ਕੇਸਾਂ ਦਾ ਫ਼ੈਸਲਾ ਕਰਨ ਦੇ ਅਧਿਕਾਰ ਕੇਵਲ ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ ਨੂੰ ਦਿੱਤੇ ਗਏ ਹਨ।'
    a,_=validate(answer('For partition cases involving non-resident Indian petitioners, the book identifies the District Revenue Officer as the deciding authority.',q),[book(q)])
    assert a.status=='answered'

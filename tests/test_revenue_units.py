import pytest
from revenue_jarvis.answer import validate
from revenue_jarvis.grounding import numeric_facts
from test_grounding import ev,reply


def test_punjabi_written_deadline_and_multiplier_are_recognized():
    facts=numeric_facts('ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਸੂਚਨਾ। ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ।')
    assert ('month','3') in facts
    assert ('multiplier','5') in facts


def test_inches_cannot_be_replaced_with_centimeters():
    q='The standard karam is 66 inches long.'
    with pytest.raises(ValueError,match='numeric|unit'):
        validate(reply('The standard karam is 66 centimeters long.',q),[ev(text=q)])


def test_kanals_and_marlas_cannot_be_swapped():
    q='The land area is 230 ਕਨਾਲ 10 ਮਰਲੇ।'
    with pytest.raises(ValueError,match='numeric|unit'):
        validate(reply('The land area is 230 ਮਰਲੇ 10 ਕਨਾਲ।',q),[ev(text=q)])


def test_multiplier_cannot_borrow_same_number_from_duration():
    q='The fine is prescribed separately. The period is 5 months.'
    with pytest.raises(ValueError,match='numeric|unit'):
        validate(reply('The fine is 5 times the fee.',q),[ev(text=q)])


def test_correct_translated_unit_and_number_pass():
    q='ਸਟੈਂਡਰਡ ਕਰਮ 66 ਇੰਚ ਦੀ ਹੈ।'
    assert validate(reply('The standard karam is 66 inches.',q),[ev(text=q)])[0].claims


def test_punjabi_number_does_not_match_prefix_of_larger_word():
    assert ('number', '5') not in numeric_facts('ਪੰਜਾਹ ਮਹੀਨੇ')
    assert ('multiplier', '5') not in numeric_facts('5 ਗੁਣਾਤਮਕ')


def test_translated_written_punjabi_deadline_passes():
    q='ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਸੂਚਨਾ ਦੇਣੀ ਹੈ।'
    assert validate(reply('The information is due within 3 months.',q),[ev(text=q)])[0].claims

import re
import tempfile
import textract
from bs4 import BeautifulSoup as bs

from .utils import (
    pdfdata_to_text,
    text_after_line_numbers,
    text_before_line_numbers,
    text_from_element_lxml,
    text_from_element_xpath,
    text_from_element_siblings_lxml,
    text_from_element_siblings_xpath,
    clean,
)


def extract_simple_pdf(data, metadata):
    return pdfdata_to_text(data)


def extract_line_numbered_pdf(data, metadata):
    return text_after_line_numbers(pdfdata_to_text(data))


def extract_line_post_numbered_pdf(data, metadata):
    return text_before_line_numbers(pdfdata_to_text(data))


def extract_sometimes_numbered_pdf(data, metadata):
    """
    A few states have bills both with numbered lines and without.
    In these cases, we need to look at the start of the lines
    to determine which extraction function to use.
    """

    pdf_text = pdfdata_to_text(data)
    lines = pdf_text.split("\n")

    # Looking for lines that begin with a number
    pattern = re.compile(r"^\s*\d+\s+(.*)", flags=re.MULTILINE)
    number_of_numbered_lines = pattern.findall(pdf_text)

    # If more than 10% of the text begins with numbers, then we are
    # probably looking at a bill with numbered lines.
    THRESHOLD_NUMBERED_PDF = 0.10

    ratio_of_numbered_lines = len(number_of_numbered_lines) / len(lines)

    if ratio_of_numbered_lines > THRESHOLD_NUMBERED_PDF:
        return extract_line_numbered_pdf(data, metadata)
    else:
        return extract_simple_pdf(data, metadata)


def extract_pre_tag_html(data, metadata):
    """
    Many states that provide bill text on HTML webpages (e.g. AK, FL)
    have the text inside <pre> tags (for preformatted text).
    """

    text_inside_matching_tag = text_from_element_lxml(data, ".//pre")
    return text_after_line_numbers(text_inside_matching_tag)


def extract_from_p_tags_html(data, metadata):
    """
    For a few states providing bill text in HTML, we just want to get all
    the text in paragraph tags on the page. There may be several paragraphs.
    """

    text = text_from_element_siblings_lxml(data, ".//p")
    return text


def extractor_for_elements_by_class(bill_text_element_class):
    return extractor_for_element_by_selector(".//div[@class='" + bill_text_element_class + "']")


def extractor_for_element_by_id(bill_text_element_id):
    return extractor_for_element_by_selector(".//div[@id='" + bill_text_element_id + "']")


def extractor_for_element_by_selector(bill_text_element_selector):
    def _my_extractor(data, metadata):
        text_inside_matching_tag = text_from_element_lxml(data, bill_text_element_selector)
        return clean(text_inside_matching_tag)

    return _my_extractor


def extractor_for_element_by_xpath(bill_text_element_selector):
    def _my_extractor(data, metadata):
        text_inside_matching_tag = text_from_element_xpath(data, bill_text_element_selector)
        return clean(text_inside_matching_tag)

    return _my_extractor


def extractor_for_elements_by_xpath(bill_text_element_selector):
    def _my_extractor(data, metadata):
        text_inside_matching_tag = text_from_element_siblings_xpath(
            data, bill_text_element_selector
        )
        return clean(text_inside_matching_tag)

    return _my_extractor


def textract_extractor(**kwargs):
    """ pass through kwargs to textextract.process """
    assert "extension" in kwargs, "Must supply extension"

    def func(data, metadata):
        with tempfile.NamedTemporaryFile(delete=False) as tmpf:
            tmpf.write(data)
            tmpf.flush()
            return textract.process(tmpf.name, **kwargs).decode()

    return func


def extract_from_code_tags_html(data, metadata):
    """
    Some states (e.g. IL) have the bill text inside
    <code> tags (as it renders as fixed-width).
    """
    text = text_from_element_siblings_lxml(data, ".//code")
    return text


def tx_txt_from_html(data, metadata):   
    """Uses BeautifulSoup to extract text for TX HTML files.
    """
    whitespace_cleaner = re.compile(r'[\t\n](?=[\n\t])')
    css_cleaner = re.compile(r'td { font-family: Courier, Arial, sans-serif; font-size: 10pt; } table { empty-cells:show; }')
    html_cleaner = re.compile(r'<!?--.+>', flags=re.DOTALL)

    soup = bs(data, 'html.parser')
    t = whitespace_cleaner.sub('', soup.text) 
    t = css_cleaner.sub('', t)
    if "<" in t:
        return html_cleaner.sub('',t)
    return t

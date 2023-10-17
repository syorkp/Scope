"""
Most libraries seem to be low level. Some approach the problem through machine learning:
https://www.posos.co/articles/how-to-extract-and-structure-text-from-pdf-files-with-python-and-machine-learning

Or a partially built software (may need to train AI models)
https://dev.konfuzio.com/sdk/tutorials/information_extraction/index.html#information-extraction-tutorials
"""

from pdfquery import PDFQuery

# pdf = PDFQuery('PDFs/0038038518759248.pdf')
# pdf.load()
# pdf.tree.write("test2.xml", pretty_print=True, encoding="utf-8")
#
# text_elements = pdf.pq('LTTextLineHorizontal')
#
#
# text = [t.text for t in text_elements[:10]]
#
# for t in text:
#     print(t)

from pdfminer.high_level import extract_text
text = extract_text('PDFs/0038038518759248.pdf')
x = True
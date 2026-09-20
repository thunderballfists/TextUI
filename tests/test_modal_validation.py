import pytest

from textui import DocumentLoader, DocumentValidationError


@pytest.mark.parametrize("markup", [
    '<ui><modal><label>Missing ID</label></modal></ui>',
    '<ui><vertical><modal id="nested"><label>Nested</label></modal></vertical></ui>',
])
def test_modal_requires_an_id_and_a_document_root(markup):
    with pytest.raises(DocumentValidationError, match="modal"):
        DocumentLoader().from_string(markup)

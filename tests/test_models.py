def test_models_module_exposes_sqlmodel_metadata():
    from lab.models import SQLModel

    assert SQLModel.metadata is not None
    # No aggregates yet — sorted_tables is empty until the schema design lands.
    assert list(SQLModel.metadata.sorted_tables) == []

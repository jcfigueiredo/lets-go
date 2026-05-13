def test_models_module_exposes_sqlmodel_metadata():
    from lab.models import SQLModel

    assert SQLModel.metadata is not None

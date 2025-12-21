def test_create_app_name(app):
    assert app.name == 'Spendoo'
    assert app.config['PROJECT_NAME'] == 'Spendoo'


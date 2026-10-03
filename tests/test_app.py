def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json == {"message": "Mini LMS API is running"}

def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {"status": "ok"}
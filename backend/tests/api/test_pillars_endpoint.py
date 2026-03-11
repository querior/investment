def test_get_pillars_endpoint(client):
  response = client.get("/api/pillars")

  assert response.status_code == 200
  data = response.json()

  assert isinstance(data, list)
  if data:
      assert "date" in data[0]
      assert "pillar" in data[0]
      assert "score" in data[0]
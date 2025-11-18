from main import app

if __name__ == "__main__":
    with app.test_client() as client:
        response = client.post("/createproject", json={
            "name": "TestProject",
            "type": "python",
            "Tag": "example"
        })

        response2 = client.post("/createproject", json={
            "name": "TestProject2",
            "type": "python",
            "Tag": "example"
        })

        print(response.get_json())
        print(response.get_json())

        response1 = client.post("/listprojects", json={
            "name": "TestProject"
        })
        print(*response1.get_json()['projects'])

        response1 = client.post("/listprojects", json={})
        print(*response1.get_json()['projects'])
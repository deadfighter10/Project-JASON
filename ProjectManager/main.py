from flask import Flask, render_template, jsonify, request
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json
from uuid import uuid4


class ProjectType(str, Enum):
    PYTHON = "python"
    JAVA = "java"
    AI = "ai"
    WEB = "web"
    MOBILE = "mobile"
    HOMELAB = "homelab"
    ALPHA = "alpha"

class Project:
    def __init__(self, name, type, tag):
        self.name = name
        self.type = type
        self.tag = tag
        self.uuid = str(uuid4())

    def create_project(self):
        project_path = storage_path / f"Project {self.name}"
        if project_path.exists():
            return 1
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "type.txt").write_text(self.type or "undefined")
        (project_path / "tag.txt").write_text(self.tag or "undefined")
        return 0

    def delete_project(self):
        project_path = storage_path / self.name
        if project_path.exists():
            for item in project_path.iterdir():
                item.unlink()
            project_path.rmdir()
            return 0
        return 1

    def json_serialize(self):
        return (self.uuid, {
            "name": self.name,
            "type": self.type,
            "tag": self.tag
        })

class ProjectManager:
    def __init__(self):
        self.projects = []

    def add_project(self, project: Project) -> None:
        self.projects.append(project)
        self.update_registry()

    def remove_project(self, project_uuid:str) -> None:
        self.projects = [p for p in self.projects if p.uuid != project_uuid]
        self.update_registry()

    def list_projects(self, name: str = None, uuid: str = None) -> list:
        if name:
            return [p.__dict__ for p in self.projects if p.name == name]
        return [p.__dict__ for p in self.projects]

    def get_project_by_uuid(self, project_uuid: str) -> Project:
        for p in self.projects:
            if p.uuid == project_uuid:
                return p
        return None

    def update_registry(self) -> None:
        registry_path = storage_path / "project_registry.json"
        registry_data = {p.uuid: p.json_serialize()[1] for p in self.projects}
        json.dump(registry_data, registry_path.open('w'), indent=4)

    def load_registry(self) -> None:
        registry_path = storage_path / "project_registry.json"
        if registry_path.exists():
            with registry_path.open('r') as f:
                registry_data = json.load(f)
                for uuid, pdata in registry_data.items():
                    project = Project(
                        name=pdata['name'],
                        type=pdata['type'],
                        tag=pdata['tag']
                    )
                    project.uuid = uuid
                    self.add_project(project)


app = Flask(__name__)

storage_path = Path("/Users/Leo/projects")
storage_path.mkdir(parents=True, exist_ok=True)

manager = ProjectManager()
manager.load_registry()

@app.route("/createproject", methods=["POST"])
def create_project():
    if request.is_json:
        data = request.get_json()
        response = {}
        projecttype = data.get('type', None)
        projecttag = data.get('Tag', None)
        projectname = data.get('name', None)

        try:
            projecttype = ProjectType(projecttype.lower())
        except ValueError:
            response['message'] = 'Invalid project type'
            response['status'] = 'Failed'
            return jsonify(response)

        project = Project(
            name=projectname,
            type=projecttype,
            tag=projecttag)

        status = project.create_project()

        if status == 1:
            response['message'] = 'Project already exists'
            response['status'] = 'Failed'
        else:
            manager.add_project(project)
            response['message'] = 'Project created'
            response['status'] = 'Successful'

        return jsonify(response)

    return jsonify({'message': 'Successful'})

@app.route("/deleteproject", methods=["POST"])
def delete_project():
    if request.is_json:
        data = request.get_json()
        response = {}
        projectname = data.get('name', None)

        project = Project(
            name=projectname,
            type=None,
            tag=None)

        status = project.delete_project()

        if status == 1:
            response['message'] = 'Project does not exist'
            response['status'] = 'Failed'
        else:
            response['message'] = 'Project deleted'
            response['status'] = 'Successful'

        return jsonify(response)

    return jsonify({'message': 'Successful'})

@app.route("/listprojects", methods=["POST"])
def list_projects():
    if request.is_json:
        data = request.get_json()
        response = {}
        name = data.get('name', None)
        if name:
            projects = manager.list_projects(name=name)
            response['projects'] = projects
            response['status'] = 'Successful'
            return jsonify(response)
        projects = manager.list_projects()
        response['projects'] = projects
        response['status'] = 'Successful'
        return jsonify(response)

if __name__ == "__main__":
    with app.test_client() as client:
        response = client.post("/createproject", json={
            "name": "TestProject",
            "type": "python",
            "Tag": "example"
        })

        response2 = client.post("/createproject", json={
            "name": "TestProject",
            "type": "python",
            "Tag": "example"
        })

        print(response.get_json())
        print(response.get_json())

        response1 = client.post("/listprojects", json={
            "name": "TestProject"
        })
        print(response1.get_json())
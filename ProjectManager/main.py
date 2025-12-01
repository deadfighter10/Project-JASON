import os
import shutil

from flask import Flask, render_template, jsonify, request
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json
from uuid import uuid4
from git import Repo
from dotenv import load_dotenv
load_dotenv()


class ProjectType(str, Enum):
    PYTHON = "python"
    JAVA = "java"
    AI = "ai"
    WEB = "web"
    MOBILE = "mobile"
    HOMELAB = "homelab"
    ALPHA = "alpha"

class Project:
    def __init__(self, name, type, tag, uuid=None):
        self.name = name
        self.type = type
        self.tag = tag
        if uuid:
            self.uuid = uuid
        else:
            self.uuid = str(uuid4())

    def create_project(self):
        project_path = storage_path / f"Project {self.name}"
        if project_path.exists():
            return 1
        try:
            project_path.mkdir(parents=True, exist_ok=True)
            repo = Repo.init(project_path)
            (project_path / "README.md").touch()
            (project_path / "README.md").write_text(f"# {self.name}\n\nType: {self.type}\nTag: {self.tag}\n")
            (project_path / "requirements.txt").touch()
            (project_path / ".gitignore").touch()
            (project_path / "Dockerfile").touch()
            (project_path / ".dockerignore").touch()
            (project_path / ".env").touch()
            return 0
        except Exception as e:
            return 2

    def delete_project(self):
        project_path = storage_path / f"Project {self.name}"
        if project_path.exists():
            try:
                shutil.rmtree(project_path)
                return 0
            except Exception as e:
                print(f"Error deleting project: {e}")
                return 1
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
            return [p.__dict__ for p in self.projects if p.name == f"{name}"]
        if uuid:
            return [p.__dict__ for p in self.projects if p.uuid == uuid]
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
                    self.projects.append(project)
        else:
            registry_path.touch()
            registry_path.write_text("{}")

app = Flask(__name__)
DEFAULT_STORAGE = "/mnt/nas/Projects"

storage_path = Path(os.environ.get("PROJECT_PATH", DEFAULT_STORAGE))
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
        elif status == 2:
            response['message'] = 'Unexpected error occurred while creating project'
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

        existing_projects = manager.list_projects(name=projectname)

        if not existing_projects:
            response['message'] = 'Project does not exist'
            response['status'] = 'Failed'
            return jsonify(response)

        # 2. Get the object so we have the correct UUID
        p_data = existing_projects[0]
        project = manager.get_project_by_uuid(p_data['uuid'])

        if not project:
            # Should not happen if list_projects found it, but safety first
            response['message'] = 'Project registry error'
            response['status'] = 'Failed'
            return jsonify(response)

        status = project.delete_project()

        if status == 1:
            response['message'] = 'Failed to delete project files'
            response['status'] = 'Failed'
        else:
            manager.remove_project(project.uuid)
            response['message'] = 'Project deleted'
            response['status'] = 'Successful'

        return jsonify(response)

    return jsonify({'message': 'Invalid request', 'status': 'Failed'})

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
    app.run(host="0.0.0.0", debug=True)
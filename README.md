# Project J.A.S.O.N.

Project J.A.S.O.N. (Just A Simple Ordinary Network) is a collection of my own (self-hosted) projects for my own intranet called J.A.S.O.N. . Feel free to contribute with pull requests or ideas or just self host it for yourself.

## Projects

### ProjectManager:
A service to manage and synchronize my own projects with the servers. I switched to Gitea, so this project is pretty much deprecated. Yes, I know this project was a dumb idea in the world of version control and the good old Github, but it was definitely fun to write, maybe I will later build a project on some sync to the server, I don't know yet.
***
### PasswordManager:
A custom lightweight terminal-based safe password storage with the following features:
- **Functions**:
    - **add**: Add a new entry
    - **get**: Read an existing entry
    - **ls**: List the existing entries names
    - **delete**: Delete an entry
    - **edit**: Edit an existing entry
- **Current Entry types**:
    - **Passwords**: ```python frontend.py add```, ```python frontend.py get```, ect...
    - **Cards**: ```python frontend.py card add```, ```python frontend.py card get```, ect...
    - **API keys**: ```python frontend.py api add```, ect...
- **Other Good tips**:
    - I do recommend using alias (I use Mac) or some kind of shortcut to use this, it makes the process faster and more user friendly, personally, I set the ```pass``` command.
    - Keep the server dumb as it is in the [server.py](PasswordManager/server.py) for safety, try not to move crypto there.

**HOW TO DEPLOY**

*SERVER*:
The folder have a [Dockerfile](PasswordManager/Dockerfile) and a [compose.yml](PasswordManager/compose.yml) file, too, so put the project files on the server, and then, on the server build and run the image (this is for Docker compose v2, please be normal and use Docker compose v2):

```docker compose up -d --build```

The base port is 3333, so make sure it is available. If you run this in an LXC, make sure the Linux kernel allows access to ports and can set them, it can cause difficulties.

*USER*:
On your computer, you need to use either venv or global python commands and run in the folder PasswordManager (I personally do not like global python, I prefer venv, but this is preference, it should work everywhere):

```pip install -r requirements.txt```

Also, you need to set the .env file in the folder based on the [.env.example](PasswordManager/.env.example)

And then, you should be set to use: 

```python frontend.py add```